# autograder

This repository contains the GW08 autograder and related grading artifacts, feedback samples, and result outputs.

## LLM provider configuration

The grader supports Claude through Anthropic's API as well as the existing OpenAI-compatible providers. Put the provider key in a local `.env` file; do not commit that file.

For Claude:

```dotenv
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-key
MODEL_NAME=claude-sonnet-5
MAX_TOKENS=4000
```

`LLM_PROVIDER=anthropic` is optional when `ANTHROPIC_API_KEY` is the only provider key present. This grader's prompts are about 4,000 input tokens plus a short JSON response, so context size is not a concern. Thinking is disabled for this task because the grader requires a compact JSON response, not a hidden reasoning trace. Sonnet is recommended because the rubric requires nuanced judgments about code indexing, look-ahead bias, rolling windows, and formulas; Haiku is faster but more likely to miss those distinctions. A Claude API key normally works only if it is active, has API credits or billing access, and the selected model is available to that account. A Claude.ai subscription or promotional credit is not automatically the same as Anthropic API credit; confirm the key's API billing/credits in the Anthropic Console.

## Contents
- `app/app.py` — Flask web application and batch endpoints
- `app/autograder.py` — main grading logic and CLI
- `config/rubric_gw.txt` — rubric used for evaluation
- `notebooks/reference/` — instructor/reference notebooks
- `notebooks/templates/` — student notebook template
- `tests/submissions/` — grading test submissions
- `scripts/estimate_api_cost.py` — token-cost estimator
- `docs/` — project documentation and implementation notes
- `results/` — grading outputs and sample LLM feedback

## Run locally

```bash
source .venv/bin/activate
python app/app.py
```

Then open `http://localhost:5050`. Keep API credentials in the local, ignored `.env` file.

## Notes
This project captures the current autograder progress and result snapshots for the ML in Finance assignment workflow.
