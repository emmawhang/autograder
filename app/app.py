import csv
import io
import json
import os
import tempfile
import uuid
import zipfile
from pathlib import Path

from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename

from autograder import (
    build_grading_prompt,
    call_llm,
    extract_notebook_content,
    load_rubric,
    markdown_feedback,
    parse_llm_json,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ASSIGNMENT_NOTEBOOK = PROJECT_ROOT / "notebooks" / "reference" / "GW08_table3_two_cols.ipynb"
RUBRIC_PATH = PROJECT_ROOT / "config" / "rubric_gw.txt"

app = Flask(__name__)
ALLOWED_EXTENSIONS = {".ipynb", ".py", ".txt", ".md"}
MAX_BATCH_FILES = 200
BATCH_RESULTS = {}


def provider_error(exc: Exception) -> str:
    message = str(exc)
    lower = message.lower()
    if "insufficient_quota" in lower or "quota" in lower or "429" in lower:
        return "The model provider is out of quota or rate-limited. Check the provider billing/credits for this API key."
    if "invalid_api_key" in lower or "incorrect api key" in lower:
        return "The API key is invalid. Update the key in .env and restart the app."
    return f"Grading failed: {message}"


def grading_context():
    assignment_text = extract_notebook_content(str(ASSIGNMENT_NOTEBOOK))["prompt_text"]
    rubric = load_rubric(str(RUBRIC_PATH))
    return assignment_text, rubric


def grade_file(path: Path, filename: str, assignment_text: str, rubric) -> dict:
    if path.suffix.lower() == ".ipynb":
        submission_text = extract_notebook_content(str(path))["prompt_text"]
    else:
        submission_text = path.read_text(encoding="utf-8", errors="replace")

    prompt = build_grading_prompt(
        assignment_text=assignment_text,
        submission_text=submission_text,
        rubric=rubric,
    )
    result = parse_llm_json(call_llm(prompt))
    result["student_file"] = filename
    return result


def manual_review_flags(result: dict) -> list[str]:
    flags = result.get("flags_for_manual_review") or []
    return [str(flag) for flag in flags]


def make_batch_zip(rows: list[dict], feedback_files: list[tuple[str, str]]) -> bytes:
    grades_buffer = io.StringIO()
    fieldnames = ["student_file", "status", "total_score", "max_score", "manual_review", "flags", "error"]
    writer = csv.DictWriter(grades_buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in fieldnames})

    review_buffer = io.StringIO()
    review_writer = csv.DictWriter(review_buffer, fieldnames=["student_file", "total_score", "flags", "reason"])
    review_writer.writeheader()
    for row in rows:
        if row.get("manual_review") == "yes":
            review_writer.writerow({
                "student_file": row["student_file"],
                "total_score": row.get("total_score", ""),
                "flags": row.get("flags", ""),
                "reason": row.get("error", "Review the flagged criteria before finalizing."),
            })

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("grades.csv", grades_buffer.getvalue())
        archive.writestr("manual_review.csv", review_buffer.getvalue())
        for filename, content in feedback_files:
            archive.writestr(filename, content)
    return output.getvalue()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/grade", methods=["POST"])
def grade_submission():
    uploaded_file = request.files.get("student_file")

    if uploaded_file is None or uploaded_file.filename == "":
        return render_template("index.html", error="Please choose a student notebook or Python file to grade."), 400

    filename = secure_filename(uploaded_file.filename)
    if not filename:
        return render_template("index.html", error="The uploaded file name is invalid."), 400

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        return render_template("index.html", error="Please upload a .ipynb, .py, .txt, or .md file."), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
        uploaded_file.save(tmp_file.name)
        temp_path = tmp_file.name

    try:
        assignment_text, rubric = grading_context()
        result = grade_file(Path(temp_path), filename, assignment_text, rubric)
        return render_template("result.html", result=result, filename=filename)
    except Exception as exc:  # pragma: no cover - kept simple for local UI display
        return render_template("index.html", error=provider_error(exc)), 200
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@app.route("/batch-grade", methods=["POST"])
def batch_grade():
    uploaded_file = request.files.get("batch_file")
    if uploaded_file is None or uploaded_file.filename == "":
        return render_template("index.html", error="Please choose a ZIP file containing student submissions."), 400
    if Path(uploaded_file.filename).suffix.lower() != ".zip":
        return render_template("index.html", error="Batch grading requires a .zip file."), 400

    try:
        assignment_text, rubric = grading_context()
        rows = []
        feedback_files = []
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "submissions.zip"
            uploaded_file.save(zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                valid_members = []
                for member in members:
                    member_path = Path(member.filename)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        continue
                    if member_path.suffix.lower() in ALLOWED_EXTENSIONS:
                        valid_members.append(member)
                if len(valid_members) > MAX_BATCH_FILES:
                    return render_template("index.html", error=f"ZIP contains too many submissions. Maximum is {MAX_BATCH_FILES}."), 400
                if not valid_members:
                    return render_template("index.html", error="ZIP contains no supported .ipynb, .py, .txt, or .md submissions."), 400

                for index, member in enumerate(valid_members, start=1):
                    filename = secure_filename(Path(member.filename).name) or f"submission_{index}.ipynb"
                    submission_path = Path(temp_dir) / f"{index}_{filename}"
                    with archive.open(member) as source, submission_path.open("wb") as target:
                        target.write(source.read())
                    try:
                        result = grade_file(submission_path, filename, assignment_text, rubric)
                        flags = manual_review_flags(result)
                        rows.append({
                            "student_file": filename,
                            "status": "graded",
                            "total_score": result.get("total_score", ""),
                            "max_score": result.get("max_score", 100),
                            "manual_review": "yes" if flags else "no",
                            "flags": " | ".join(flags),
                            "error": "",
                        })
                        stem = Path(filename).stem
                        feedback_files.append((f"feedback/{stem}.json", json.dumps(result, indent=2, ensure_ascii=False)))
                        feedback_files.append((f"feedback/{stem}.md", markdown_feedback(result)))
                    except Exception as exc:
                        error = provider_error(exc)
                        rows.append({
                            "student_file": filename,
                            "status": "failed",
                            "total_score": "",
                            "max_score": 100,
                            "manual_review": "yes",
                            "flags": "grading error",
                            "error": error,
                        })

        batch_id = uuid.uuid4().hex
        BATCH_RESULTS[batch_id] = make_batch_zip(rows, feedback_files)
        return render_template("batch_result.html", rows=rows, batch_id=batch_id)
    except (zipfile.BadZipFile, OSError) as exc:
        return render_template("index.html", error=f"Could not read the ZIP file: {exc}"), 400
    except Exception as exc:  # pragma: no cover - kept simple for local UI display
        return render_template("index.html", error=provider_error(exc)), 200


@app.route("/batch-download/<batch_id>", methods=["GET"])
def batch_download(batch_id):
    archive = BATCH_RESULTS.get(batch_id)
    if archive is None:
        return "Batch result expired or not found.", 404
    return send_file(
        io.BytesIO(archive),
        mimetype="application/zip",
        as_attachment=True,
        download_name="gw08_batch_results.zip",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
