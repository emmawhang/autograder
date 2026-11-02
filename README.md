# ML in Finance Notebook Autograder

This project grades student notebooks against an instructor-provided answer-key notebook. The key is the primary reference: its questions, solution code, explanations, outputs, grading criteria, and point allocations are included in the Claude prompt.

## Workflow

1. Start the Flask app:

   ```bash
   source .venv/bin/activate
   python app/app.py
   ```

2. Open `http://localhost:5050`.
3. Upload an instructor key notebook with either a single student notebook or a ZIP of submissions.
4. Review question-level scores, deductions, feedback, and manual-review flags.
5. Download the batch ZIP when grading a class.

The bundled GW08 key is used only as a CLI default. New assignments should provide a new key notebook at runtime.

## Problem-set folders and Brightspace feedback

Each problem set can be graded from a stable folder:

```text
problem_sets/ps1/
  ps1_key.ipynb
  submissions/
  results/
```

Place a few notebooks in `submissions/` while testing, then use **Grade problem-set folder**. The `results/` folder receives:

- `grades.csv` with student identifiers, total scores, question-level scores, and complete plain-text feedback
- One `.txt` feedback file per student for Brightspace's Overall Feedback field
- JSON audit files and optional Markdown feedback

For a Brightspace download, use **Brightspace feedback ZIP** and select the problem set. The app preserves the original ZIP paths and submission filenames and adds `grading_feedback.txt` inside each student's original folder. Review the generated ZIP before uploading it with Brightspace's **Add Feedback Files** workflow. Brightspace requires downloaded submission files and their identifying folder/file names to remain unchanged.

The equivalent endpoint is:

```bash
curl -X POST \
  -F problem_set=ps1 \
  -F brightspace_file=@brightspace_download.zip \
  http://127.0.0.1:5050/brightspace-grade
```

Brightspace documentation: [Evaluate assignments using the Assignments tool](https://community.d2l.com/brightspace/kb/articles/3529-evaluate-assignments-using-the-assignments-tool).

## Key notebook requirements

The parser recognizes ordinary Markdown headings, question/task headings, code cells, outputs, and explanatory text. For authoritative scores, include explicit criteria and point allocations, for example:

```markdown
## Question 1 — Predictor construction — 15 points

### Grading criteria
- 5 points: ...
- 10 points: ...
```

If the key has no explicit criteria or points, the grader flags the report for instructor review and does not silently invent authoritative weights. An optional supplemental JSON rubric can be supplied through the CLI.

## CLI

```bash
PYTHONPATH=app python app/autograder.py \
  --key path/to/instructor_key.ipynb \
  --submission path/to/student_submission.ipynb \
  --rubric config/rubric_gw.txt \
  --json-out grading_outputs/student.json \
  --md-out grading_outputs/student.md
```

`--assignment` remains an alias for `--key` for compatibility with older scripts.

## Project structure

```text
app/
  app.py                 Flask routes and upload handling
  notebook_parser.py     Notebook validation and cell extraction
  reference_extractor.py Key criteria and point extraction
  grading.py             Prompt construction, provider calls, and report formatting
  autograder.py          CLI compatibility wrapper
  templates/             Web pages
config/
  rubric_gw.txt          Optional supplemental GW08 rubric
notebooks/
  reference/             Reusable instructor/reference notebooks
  templates/             Student distribution templates
```

## Configuration and security

Store provider credentials only in the ignored local `.env` file. Supported providers include Anthropic and OpenAI-compatible endpoints:

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
MODEL_NAME=claude-sonnet-5
MAX_TOKENS=4000
```

Student submissions and generated reports are ignored by Git. Uploaded files are processed in temporary directories and are not retained by the application.
