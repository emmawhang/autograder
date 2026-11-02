"""Flask interface for key-notebook-driven grading."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterator

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from grading import attach_reference_flags, build_grading_prompt, call_llm, markdown_feedback, parse_llm_json
from notebook_parser import NotebookParseError, extract_notebook_content
from autograder import load_rubric

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KEY = PROJECT_ROOT / "notebooks" / "reference" / "GW08_table3_two_cols.ipynb"
DEFAULT_RUBRIC = PROJECT_ROOT / "config" / "rubric_gw.txt"
ALLOWED_EXTENSIONS = {".ipynb", ".py", ".txt", ".md"}
MAX_BATCH_FILES = 200
BATCH_RESULTS: Dict[str, bytes] = {}

app = Flask(__name__)


def provider_error(exc: Exception) -> str:
	message = str(exc)
	lower = message.lower()
	if "quota" in lower or "429" in lower:
		return "The model provider is out of quota or rate-limited."
	if "api_key" in lower:
		return "The API key is invalid or missing. Check the local .env file."
	if isinstance(exc, NotebookParseError):
		return message
	return f"Grading failed: {message}"


def _write_upload(uploaded_file: Any, suffix: str) -> str:
	handle = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
	try:
		uploaded_file.save(handle)
	finally:
		handle.close()
	return handle.name


def _key_path_from_request() -> tuple[str, bool]:
	uploaded = request.files.get("key_file")
	if uploaded and uploaded.filename:
		filename = secure_filename(uploaded.filename)
		if not filename or Path(filename).suffix.lower() != ".ipynb":
			raise ValueError("The instructor key must be a valid .ipynb file.")
		return _write_upload(uploaded, ".ipynb"), True
	key_path = request.form.get("key_path", "").strip()
	if key_path:
		path = Path(key_path).expanduser().resolve()
		if path.suffix.lower() != ".ipynb" or not path.is_file():
			raise ValueError("The selected key notebook does not exist or is not .ipynb.")
		return str(path), False
	if DEFAULT_KEY.is_file():
		return str(DEFAULT_KEY), False
	raise ValueError("Upload or select an instructor key notebook before grading.")


def _grade_file(path: Path, filename: str, key_content: Dict[str, Any], rubric: Dict[str, Any] | None) -> dict:
	if path.suffix.lower() == ".ipynb":
		submission = extract_notebook_content(str(path))
	else:
		submission = {"prompt_text": path.read_text(encoding="utf-8", errors="replace")}
	result = attach_reference_flags(
		parse_llm_json(call_llm(build_grading_prompt(key_content, submission, rubric))),
		key_content,
	)
	result["student_file"] = filename
	return result


def _valid_zip_members(archive: zipfile.ZipFile) -> Iterator[zipfile.ZipInfo]:
	for member in archive.infolist():
		path = Path(member.filename)
		if member.is_dir() or path.is_absolute() or ".." in path.parts:
			continue
		if path.suffix.lower() in ALLOWED_EXTENSIONS:
			yield member


def _batch_zip(rows: list[dict], feedback_files: list[tuple[str, str]]) -> bytes:
	grades = io.StringIO()
	writer = csv.DictWriter(grades, fieldnames=["student_file", "status", "total_score", "max_score", "manual_review", "flags", "error"])
	writer.writeheader()
	for row in rows:
		writer.writerow({field: row.get(field, "") for field in writer.fieldnames})
	output = io.BytesIO()
	with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr("grades.csv", grades.getvalue())
		for filename, content in feedback_files:
			archive.writestr(filename, content)
	return output.getvalue()


@app.route("/", methods=["GET"])
def index():
	return render_template("index.html", default_key=str(DEFAULT_KEY) if DEFAULT_KEY.is_file() else "")


@app.route("/grade", methods=["POST"])
def grade_submission():
	student = request.files.get("student_file")
	if student is None or not student.filename:
		return render_template("index.html", error="Choose a student notebook or source file.")
	filename = secure_filename(student.filename)
	if not filename or Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
		return render_template("index.html", error="Upload a supported .ipynb, .py, .txt, or .md file.")
	temp_paths: list[str] = []
	try:
		key_path, uploaded_key = _key_path_from_request()
		if uploaded_key:
			temp_paths.append(key_path)
		student_path = _write_upload(student, Path(filename).suffix.lower())
		temp_paths.append(student_path)
		key_content = extract_notebook_content(key_path)
		rubric = load_rubric(str(DEFAULT_RUBRIC)) if DEFAULT_RUBRIC.is_file() else None
		result = _grade_file(Path(student_path), filename, key_content, rubric)
		return render_template("result.html", result=result, filename=filename)
	except Exception as exc:
		return render_template("index.html", error=provider_error(exc)), 400
	finally:
		for path in temp_paths:
			try:
				os.unlink(path)
			except OSError:
				pass


@app.route("/batch-grade", methods=["POST"])
def batch_grade():
	uploaded = request.files.get("batch_file")
	if uploaded is None or not uploaded.filename or Path(uploaded.filename).suffix.lower() != ".zip":
		return render_template("index.html", error="Upload a ZIP containing student submissions."), 400
	temp_paths: list[str] = []
	try:
		key_path, uploaded_key = _key_path_from_request()
		if uploaded_key:
			temp_paths.append(key_path)
		key_content = extract_notebook_content(key_path)
		rubric = load_rubric(str(DEFAULT_RUBRIC)) if DEFAULT_RUBRIC.is_file() else None
		zip_path = _write_upload(uploaded, ".zip")
		temp_paths.append(zip_path)
		rows: list[dict] = []
		feedback_files: list[tuple[str, str]] = []
		with tempfile.TemporaryDirectory() as temp_dir, zipfile.ZipFile(zip_path) as archive:
			members = list(_valid_zip_members(archive))
			if not members:
				return render_template("index.html", error="ZIP contains no supported submissions."), 400
			if len(members) > MAX_BATCH_FILES:
				return render_template("index.html", error=f"ZIP contains more than {MAX_BATCH_FILES} submissions."), 400
			for index, member in enumerate(members, 1):
				filename = secure_filename(Path(member.filename).name) or f"submission_{index}.ipynb"
				path = Path(temp_dir) / f"{index}_{filename}"
				with archive.open(member) as source, path.open("wb") as target:
					target.write(source.read())
				try:
					result = _grade_file(path, filename, key_content, rubric)
					flags = result.get("flags_for_manual_review") or []
					rows.append({"student_file": filename, "status": "graded", "total_score": result.get("total_score", ""),
						"max_score": result.get("max_score", 0), "manual_review": "yes" if flags else "no",
						"flags": " | ".join(map(str, flags)), "error": ""})
					stem = Path(filename).stem
					feedback_files.extend([(f"feedback/{stem}.json", json.dumps(result, indent=2)),
						(f"feedback/{stem}.md", markdown_feedback(result))])
				except Exception as exc:
					rows.append({"student_file": filename, "status": "failed", "total_score": "", "max_score": "",
						"manual_review": "yes", "flags": "grading error", "error": provider_error(exc)})
		batch_id = uuid.uuid4().hex
		BATCH_RESULTS[batch_id] = _batch_zip(rows, feedback_files)
		return render_template("batch_result.html", rows=rows, batch_id=batch_id)
	except (OSError, zipfile.BadZipFile) as exc:
		return render_template("index.html", error=f"Could not read the ZIP file: {exc}"), 400
	except Exception as exc:
		return render_template("index.html", error=provider_error(exc)), 400
	finally:
		for path in temp_paths:
			try:
				os.unlink(path)
			except OSError:
				pass


@app.route("/batch-download/<batch_id>", methods=["GET"])
def batch_download(batch_id: str):
	archive = BATCH_RESULTS.get(batch_id)
	if archive is None:
		return "Batch result expired or not found.", 404
	return send_file(io.BytesIO(archive), mimetype="application/zip", as_attachment=True, download_name="grading_results.zip")


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5050")), debug=False, use_reloader=False)
