import os
import tempfile
from pathlib import Path

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

from autograder import (
    build_grading_prompt,
    call_llm,
    extract_notebook_content,
    load_rubric,
    parse_llm_json,
)

BASE_DIR = Path(__file__).resolve().parent
ASSIGNMENT_NOTEBOOK = BASE_DIR / "GW08_table3_two_cols.ipynb"
RUBRIC_PATH = BASE_DIR / "rubric_gw.txt"

app = Flask(__name__)


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
    if extension not in {".ipynb", ".py", ".txt", ".md"}:
        return render_template("index.html", error="Please upload a .ipynb, .py, .txt, or .md file."), 400

    with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp_file:
        uploaded_file.save(tmp_file.name)
        temp_path = tmp_file.name

    try:
        assignment_text = extract_notebook_content(str(ASSIGNMENT_NOTEBOOK))["prompt_text"]
        rubric = load_rubric(str(RUBRIC_PATH))

        if extension == ".ipynb":
            submission_text = extract_notebook_content(temp_path)["prompt_text"]
        else:
            submission_text = Path(temp_path).read_text(encoding="utf-8", errors="replace")

        prompt = build_grading_prompt(
            assignment_text=assignment_text,
            submission_text=submission_text,
            rubric=rubric,
        )

        llm_response = call_llm(prompt)
        result = parse_llm_json(llm_response)
        return render_template("result.html", result=result, filename=filename)
    except Exception as exc:  # pragma: no cover - kept simple for local UI display
        message = str(exc)
        lower = message.lower()
        if "insufficient_quota" in lower or "quota" in lower or "429" in lower:
            friendly = "The model provider is out of quota. Add billing to your OpenAI account or switch to a different valid API key."
        elif "invalid_api_key" in lower or "incorrect api key" in lower:
            friendly = "The API key is invalid. Update the key in .env and restart the app."
        else:
            friendly = f"Grading failed: {message}"

        return render_template("index.html", error=friendly), 200
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
