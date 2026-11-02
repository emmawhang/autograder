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

from grading import (
	attach_reference_flags,
	build_grading_prompt,
	call_llm,
	markdown_feedback,
	parse_llm_json,
	plain_text_feedback,
)
from notebook_parser import NotebookParseError, extract_notebook_content
from autograder import load_rubric

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROBLEM_SETS_ROOT = PROJECT_ROOT / "problem_sets"
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


def _problem_set_path(name: str) -> Path:
	candidate = (PROBLEM_SETS_ROOT / name).resolve()
	if PROBLEM_SETS_ROOT.resolve() not in candidate.parents or not candidate.is_dir():
		raise ValueError("Unknown problem set. Choose a directory under problem_sets/.")
	return candidate


def _folder_key(problem_set: Path) -> Path:
	keys = sorted(
		path for path in problem_set.glob("*_key.ipynb")
		if path.is_file() and path.resolve().parent == problem_set.resolve()
	)
	if len(keys) != 1:
		raise ValueError(
			f"{problem_set.name} must contain exactly one *_key.ipynb file; found {len(keys)}."
		)
	return keys[0]


def _folder_submissions(problem_set: Path) -> Path:
	path = problem_set / "submissions"
	path.mkdir(exist_ok=True)
	return path


def _folder_results(problem_set: Path) -> Path:
	path = problem_set / "results"
	path.mkdir(exist_ok=True)
	return path


def _grade_folder(problem_set_name: str) -> list[dict]:
	problem_set = _problem_set_path(problem_set_name)
	key_content = extract_notebook_content(str(_folder_key(problem_set)))
	rubric = load_rubric(str(DEFAULT_RUBRIC)) if DEFAULT_RUBRIC.is_file() else None
	submissions = sorted(
		path for path in _folder_submissions(problem_set).iterdir()
		if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
	)
	if not submissions:
		raise ValueError(f"No supported submissions found in {problem_set}/submissions/.")

	results_dir = _folder_results(problem_set)
	rows: list[dict] = []
	for path in submissions:
		try:
			result = _grade_file(path, path.name, key_content, rubric)
			stem = secure_filename(path.stem) or "submission"
			(results_dir / f"{stem}.json").write_text(
				json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
			)
			(results_dir / f"{stem}.md").write_text(markdown_feedback(result), encoding="utf-8")
			feedback_text = plain_text_feedback(result)
			(results_dir / f"{stem}.txt").write_text(feedback_text, encoding="utf-8")
			flags = result.get("flags_for_manual_review") or []
			rows.append({
				"student_file": path.name,
				"status": "graded",
				"total_score": result.get("total_score", ""),
				"max_score": result.get("max_score", 0),
				"manual_review": "yes" if flags else "no",
				"flags": " | ".join(map(str, flags)),
				"error": "",
				"feedback": feedback_text,
				"result": result,
			})
		except Exception as exc:
			rows.append({
				"student_file": path.name,
				"status": "failed",
				"total_score": "",
				"max_score": "",
				"manual_review": "yes",
				"flags": "grading error",
				"error": provider_error(exc),
				"feedback": provider_error(exc),
				"result": {},
			})

	(results_dir / "grades.csv").write_text(
		_csv_text(rows), encoding="utf-8"
	)
	return rows


def _csv_text(rows: list[dict]) -> str:
	buffer = io.StringIO()
	question_names = []
	for row in rows:
		for item in (row.get("result") or {}).get("question_scores", []) or (row.get("result") or {}).get("breakdown", []):
			name = str(item.get("question", item.get("criterion", "Question")))
			if name not in question_names:
				question_names.append(name)
			for subquestion in item.get("subquestions", []):
				sub_name = f"{name} {subquestion['label']}"
				if sub_name not in question_names:
					question_names.append(sub_name)
	fields = ["student_identifier", "total_score", "max_score"] + question_names + ["full_feedback", "status", "manual_review", "flags", "error"]
	writer = csv.DictWriter(
		buffer,
		fieldnames=fields,
		extrasaction="ignore",
	)
	writer.writeheader()
	for row in rows:
		result = row.get("result") or {}
		scores = {}
		for item in result.get("question_scores", []) or result.get("breakdown", []):
			name = str(item.get("question", item.get("criterion", "Question")))
			scores[name] = f"{item.get('score', 0)}/{item.get('max_score', 0)}"
			for subquestion in item.get("subquestions", []):
				scores[f"{name} {subquestion['label']}"] = (
					f"{subquestion['score']}/{subquestion['max_score']}"
				)
		writer.writerow({
			"student_identifier": row.get("student_file", ""),
			"total_score": row.get("total_score", ""),
			"max_score": row.get("max_score", ""),
			**scores,
			"full_feedback": row.get("feedback", row.get("error", "")),
			"status": row.get("status", ""),
			"manual_review": row.get("manual_review", ""),
			"flags": row.get("flags", ""),
			"error": row.get("error", ""),
		})
	return buffer.getvalue()


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
	grades = _csv_text(rows)
	output = io.BytesIO()
	with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
		archive.writestr("grades.csv", grades)
		for filename, content in feedback_files:
			archive.writestr(filename, content)
	return output.getvalue()


def _brightspace_feedback_zip(
	archive: zipfile.ZipFile,
	key_content: Dict[str, Any],
	rubric: Dict[str, Any] | None,
	results_dir: Path,
) -> tuple[bytes, list[dict]]:
	"""Grade a downloaded Brightspace ZIP and preserve every original path."""
	output = io.BytesIO()
	rows: list[dict] = []
	feedback_by_folder: dict[str, str] = {}
	with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as destination:
		members = [
			member for member in _valid_zip_members(archive)
			if Path(member.filename).suffix.lower() == ".ipynb"
		]
		if not members:
			raise ValueError("Brightspace ZIP contains no supported submissions.")
		for member in archive.infolist():
			if member.is_dir():
				destination.writestr(member, b"")
				continue
			data = archive.read(member)
			destination.writestr(member, data)
		for member in members:
			filename = Path(member.filename).name
			file_descriptor, temp_name = tempfile.mkstemp(suffix=Path(filename).suffix)
			os.close(file_descriptor)
			temp_path = Path(temp_name)
			try:
				temp_path.write_bytes(archive.read(member))
				result = _grade_file(temp_path, filename, key_content, rubric)
				feedback = plain_text_feedback(result)
				folder = str(Path(member.filename).parent)
				feedback_by_folder[folder] = feedback
				flags = result.get("flags_for_manual_review") or []
				rows.append({
					"student_file": filename,
					"status": "graded",
					"total_score": result.get("total_score", ""),
					"max_score": result.get("max_score", 0),
					"manual_review": "yes" if flags else "no",
					"flags": " | ".join(map(str, flags)),
					"error": "",
					"feedback": feedback,
					"result": result,
				})
				stem = secure_filename(Path(filename).stem) or "submission"
				(results_dir / f"{stem}.txt").write_text(feedback, encoding="utf-8")
				(results_dir / f"{stem}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
			except Exception as exc:
				rows.append({
					"student_file": filename,
					"status": "failed",
					"total_score": "",
					"max_score": "",
					"manual_review": "yes",
					"flags": "grading error",
					"error": provider_error(exc),
					"feedback": provider_error(exc),
					"result": {},
				})
			finally:
				temp_path.unlink(missing_ok=True)
		for folder, feedback in feedback_by_folder.items():
			target = f"{folder}/grading_feedback.txt" if folder != "." else "grading_feedback.txt"
			destination.writestr(target, feedback)
	return output.getvalue(), rows


@app.route("/", methods=["GET"])
def index():
	problem_sets = sorted(
		path.name for path in PROBLEM_SETS_ROOT.iterdir()
		if path.is_dir() and not path.name.startswith(".")
	) if PROBLEM_SETS_ROOT.is_dir() else []
	return render_template(
		"index.html",
		default_key=str(DEFAULT_KEY) if DEFAULT_KEY.is_file() else "",
		problem_sets=problem_sets,
	)


@app.route("/folder-grade", methods=["POST"])
def folder_grade():
	problem_set = request.form.get("problem_set", "").strip()
	if not problem_set:
		return render_template("index.html", error="Choose a problem set folder first."), 400
	try:
		rows = _grade_folder(problem_set)
		return render_template("batch_result.html", rows=rows, batch_id=None, problem_set=problem_set)
	except Exception as exc:
		return render_template("index.html", error=provider_error(exc)), 400


@app.route("/brightspace-grade", methods=["POST"])
def brightspace_grade():
	problem_set_name = request.form.get("problem_set", "").strip()
	uploaded = request.files.get("brightspace_file")
	if not problem_set_name or uploaded is None or not uploaded.filename:
		return render_template("index.html", error="Choose a problem set and Brightspace ZIP."), 400
	if Path(uploaded.filename).suffix.lower() != ".zip":
		return render_template("index.html", error="Brightspace upload must be a .zip file."), 400
	try:
		problem_set = _problem_set_path(problem_set_name)
		key_content = extract_notebook_content(str(_folder_key(problem_set)))
		rubric = load_rubric(str(DEFAULT_RUBRIC)) if DEFAULT_RUBRIC.is_file() else None
		zip_path = _write_upload(uploaded, ".zip")
		try:
			with zipfile.ZipFile(zip_path) as archive:
				brightspace_zip, rows = _brightspace_feedback_zip(
					archive, key_content, rubric, _folder_results(problem_set)
				)
		finally:
			os.unlink(zip_path)
		(problem_set / "results" / "brightspace_grades.csv").write_text(
			_csv_text(rows), encoding="utf-8"
		)
		download_id = uuid.uuid4().hex
		BATCH_RESULTS[download_id] = brightspace_zip
		return render_template(
			"batch_result.html", rows=rows, batch_id=download_id, problem_set=problem_set_name
		)
	except Exception as exc:
		return render_template("index.html", error=provider_error(exc)), 400


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
					feedback = plain_text_feedback(result)
					rows.append({"student_file": filename, "status": "graded", "total_score": result.get("total_score", ""),
						"max_score": result.get("max_score", 0), "manual_review": "yes" if flags else "no",
						"flags": " | ".join(map(str, flags)), "error": "", "feedback": feedback, "result": result})
					stem = Path(filename).stem
					feedback_files.extend([(f"feedback/{stem}.json", json.dumps(result, indent=2)),
						(f"feedback/{stem}.md", markdown_feedback(result)),
						(f"feedback/{stem}.txt", feedback)])
				except Exception as exc:
					rows.append({"student_file": filename, "status": "failed", "total_score": "", "max_score": "",
						"manual_review": "yes", "flags": "grading error", "error": provider_error(exc),
						"feedback": provider_error(exc), "result": {}})
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
