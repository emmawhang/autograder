import argparse
import json
import os
from typing import Any, Dict, List

import nbformat
from dotenv import load_dotenv
from openai import OpenAI


REQUIRED_OUTPUT_SCHEMA: Dict[str, Any] = {
	"total_score": 0,
	"max_score": 100,
	"breakdown": [
		{
			"criterion": "string",
			"score": 0,
			"max_score": 0,
			"reason": "string",
		}
	],
	"final_feedback": "string",
	"flags_for_manual_review": ["string"],
}


def load_notebook(path: str) -> nbformat.NotebookNode:
	with open(path, "r", encoding="utf-8") as file:
		return nbformat.read(file, as_version=4)


def _extract_cell_output_text(outputs: List[Dict[str, Any]]) -> str:
	extracted: List[str] = []
	for output in outputs or []:
		output_type = output.get("output_type", "")

		if output_type == "stream":
			text = output.get("text", "")
			if isinstance(text, list):
				text = "".join(text)
			extracted.append(str(text))
			continue

		if output_type in {"execute_result", "display_data"}:
			data = output.get("data", {})
			if "text/plain" in data:
				plain = data["text/plain"]
				if isinstance(plain, list):
					plain = "".join(plain)
				extracted.append(str(plain))
			continue

		if output_type == "error":
			ename = output.get("ename", "Error")
			evalue = output.get("evalue", "")
			traceback = output.get("traceback", [])
			traceback_text = "\n".join(traceback) if traceback else ""
			extracted.append(f"{ename}: {evalue}\n{traceback_text}".strip())

	return "\n".join(part for part in extracted if part).strip()


def extract_notebook_content(path: str) -> Dict[str, Any]:
	notebook = load_notebook(path)

	markdown_cells: List[str] = []
	code_cells: List[str] = []
	outputs: List[str] = []
	all_cells_for_prompt: List[str] = []

	for index, cell in enumerate(notebook.cells, start=1):
		source = cell.get("source", "")
		if isinstance(source, list):
			source = "".join(source)

		cell_type = cell.get("cell_type")
		if cell_type == "markdown":
			markdown_cells.append(source)
			all_cells_for_prompt.append(f"[Markdown Cell {index}]\n{source}".strip())
		elif cell_type == "code":
			code_cells.append(source)
			all_cells_for_prompt.append(f"[Code Cell {index}]\n{source}".strip())
			output_text = _extract_cell_output_text(cell.get("outputs", []))
			if output_text:
				outputs.append(f"[Outputs Cell {index}]\n{output_text}")

	return {
		"path": path,
		"num_cells": len(notebook.cells),
		"markdown_cells": markdown_cells,
		"code_cells": code_cells,
		"outputs": outputs,
		"prompt_text": "\n\n".join(all_cells_for_prompt + outputs).strip(),
	}


def load_rubric(path: str) -> Dict[str, Any]:
	with open(path, "r", encoding="utf-8") as file:
		return json.load(file)


def build_grading_prompt(
	assignment_text: str,
	submission_text: str,
	rubric: Dict[str, Any],
) -> str:
	grading_rules = """
You are grading a finance replication assignment: Goyal & Welch Table 3 (two columns: IS_R2_head and OOS_R2_head).

SCOPE: This is NOT about tangency portfolios, Sharpe ratios, equal-weight portfolios, or optimization.

CRITICAL RULES (apply these strictly):

1. LOOK-AHEAD BIAS: Penalize heavily (0/10 for the criterion) if code uses:
   - Future predictor values in forecasting loop (e.g., ts_df.iloc[pos+1][var] used to predict month pos+1)
   - Future data in benchmark calculation (e.g., mean calculated using data up to end date, not just past data)
   - Off-by-one indexing that leaks future months into training
   FLAG FOR MANUAL REVIEW if suspicious but unclear.

2. OOS ROLLING WINDOW (240-month / 20-year strict):
   - For each month t, fit model ONLY on months [t-240 : t]
   - Predict month t+1 using fitted model and past predictors (≤ lag month)
   - Mean benchmark must use ONLY months [t-240 : t], not full history
   - Deduct points if using expanding window, short window (<240), or including future data

3. ADJUSTED R2 FORMULAS:
   - In-sample: R² - (1-R²)*(T-k)/(T-1)  [uses MINUS, not plus; k=2 for intercept+1 predictor]
   - OOS: first compute 1 - (MSE_model / MSE_mean), THEN apply adjustment formula
   - Award 0 points if formula uses +, wrong k, or different formula
   - Report results in PERCENT (multiply by 100): e.g., 5.43, not 0.0543

4. BENCHMARK: MUST be historical mean = mean of past equity premiums [t-240 : t]
   - Award 0/5 if using median, trimmed mean, or future data
   - Award 2/5 if using rolling mean instead of expanding historical mean

5. VARIABLE NAMES:
   - Accept equivalent names if logic is correct: 'epremium' ↔ 'equity_premium', 'log_ratio' ↔ 'log(D/Index)'
   - Penalize ONLY if mismatch breaks final output (e.g., df_results cannot be graded)

6. LAGGING:
   - Most predictors: .shift(1)
   - Inflation ('infl'): .shift(2)
   - Award 0/10 if no lagging OR lagging applied inconsistently

7. SIGN RESTRICTION (if present):
   - Estimate sign from in-sample regression
   - During OOS: IF coefficient changes sign, set coefficient to 0 BEFORE prediction
   - Award 0/5 if applied after prediction or to predicted values instead of coefficients

8. FINAL TABLE:
   - Must have predictor names as row index
   - Exactly two columns: IS_R2_head and OOS_R2_head
   - All values numeric, reported in percent
   - Award 0/10 if transposed, has NaN, or scale is wrong (decimals vs percent)

9. NUMERICAL TOLERANCE: ±0.5% acceptable due to rounding/data handling
   - BUT: conceptual errors (wrong formula, wrong benchmark, look-ahead) are NOT tolerated

Output requirements:
- Return valid JSON only.
- Do not wrap JSON in markdown fences.
- Follow this exact shape and field names:
"""

	schema_text = json.dumps(REQUIRED_OUTPUT_SCHEMA, indent=2)
	rubric_text = json.dumps(rubric, indent=2)

	prompt = f"""
{grading_rules}
{schema_text}

Rubric JSON:
{rubric_text}

Original assignment notebook content:
{assignment_text}

Student submission notebook content:
{submission_text}

Grade now and return only JSON.
""".strip()

	return prompt


def call_llm(prompt: str) -> str:
	load_dotenv()

	groq_key = os.getenv("GROQ_API_KEY", "").strip()
	api_key = REDACTED
		groq_key
		or os.getenv("OPENAI_API_KEY", "").strip()
		or os.getenv("GROK_API_KEY", "").strip()
	)
	model_name = os.getenv("MODEL_NAME", "").strip()

	base_url = (
		os.getenv("GROQ_BASE_URL", "").strip()
		or os.getenv("OPENAI_BASE_URL", "").strip()
		or os.getenv("GROK_BASE_URL", "").strip()
	)

	if groq_key:
		base_url = "https://api.groq.com/openai/v1"
	elif not base_url:
		base_url = "https://api.openai.com/v1"

	if not api_key:
		REDACTED"Missing API key. Set GROQ_API_KEY or another OpenAI-compatible API key in .env.")

	if not model_name:
		raise ValueError("Missing MODEL_NAME in .env.")

	client_kwargs: Dict[str, Any] = {"api_key": REDACTED
	if base_url:
		client_kwargs["base_url"] = base_url

	client = OpenAI(**client_kwargs)

	response = client.chat.completions.create(
		model=model_name,
		messages=[
			{
				"role": "system",
				"content": "You are a strict grading assistant. Return valid JSON only, no extra text.",
			},
			{
				"role": "user",
				"content": prompt,
			},
		],
		temperature=0,
	)

	content = response.choices[0].message.content
	if content is None:
		raise ValueError("LLM returned empty content.")
	return content


def parse_llm_json(response: str) -> Dict[str, Any]:
	cleaned = response.strip()

	if cleaned.startswith("```"):
		lines = cleaned.splitlines()
		if lines and lines[0].startswith("```"):
			lines = lines[1:]
		if lines and lines[-1].startswith("```"):
			lines = lines[:-1]
		cleaned = "\n".join(lines).strip()

	try:
		parsed = json.loads(cleaned)
	except json.JSONDecodeError as exc:
		raise ValueError(f"Failed to parse LLM JSON response: {exc}\nRaw response:\n{response}") from exc

	required_top_keys = {
		"total_score",
		"max_score",
		"breakdown",
		"final_feedback",
		"flags_for_manual_review",
	}
	missing = required_top_keys - set(parsed.keys())
	if missing:
		raise ValueError(f"LLM JSON is missing required keys: {sorted(missing)}")

	return parsed


def save_json(result: Dict[str, Any], output_path: str) -> None:
	with open(output_path, "w", encoding="utf-8") as file:
		json.dump(result, file, indent=2, ensure_ascii=False)


def save_markdown_feedback(result: Dict[str, Any], output_path: str) -> None:
	total_score = result.get("total_score", 0)
	max_score = result.get("max_score", 100)
	breakdown = result.get("breakdown", [])
	final_feedback = result.get("final_feedback", "")
	flags = result.get("flags_for_manual_review", [])

	lines: List[str] = []
	lines.append("# GW08 Autograder Feedback")
	lines.append("")
	lines.append(f"## Score: {total_score}/{max_score}")
	lines.append("")
	lines.append("## Rubric Breakdown")
	lines.append("")

	if breakdown:
		for item in breakdown:
			criterion = item.get("criterion", "Unknown criterion")
			score = item.get("score", 0)
			item_max = item.get("max_score", 0)
			reason = item.get("reason", "")
			lines.append(f"- **{criterion}**: {score}/{item_max}")
			lines.append(f"  - Reason: {reason}")
	else:
		lines.append("- No breakdown was returned by the grader.")

	lines.append("")
	lines.append("## Final Feedback")
	lines.append("")
	lines.append(final_feedback if final_feedback else "No final feedback provided.")
	lines.append("")
	lines.append("## Flags For Manual Review")
	lines.append("")

	if flags:
		for flag in flags:
			lines.append(f"- {flag}")
	else:
		lines.append("- None")

	with open(output_path, "w", encoding="utf-8") as file:
		file.write("\n".join(lines).rstrip() + "\n")


def run_autograder(
	assignment_notebook_path: str,
	submission_notebook_path: str,
	rubric_path: str,
	json_output_path: str,
	markdown_output_path: str,
) -> Dict[str, Any]:
	assignment_content = extract_notebook_content(assignment_notebook_path)
	submission_content = extract_notebook_content(submission_notebook_path)
	rubric = load_rubric(rubric_path)

	prompt = build_grading_prompt(
		assignment_text=assignment_content["prompt_text"],
		submission_text=submission_content["prompt_text"],
		rubric=rubric,
	)

	llm_response = call_llm(prompt)
	parsed_result = parse_llm_json(llm_response)

	save_json(parsed_result, json_output_path)
	save_markdown_feedback(parsed_result, markdown_output_path)

	return parsed_result


def _build_arg_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description=(
			"GW08 LLM-based autograder for Table 3 replication "
			"(IS_R2_head and OOS_R2_head)."
		)
	)
	parser.add_argument(
		"--assignment",
		default="GW08_table3_two_cols.ipynb",
		help="Path to original assignment notebook.",
	)
	parser.add_argument(
		"--submission",
		default="sample_student_submission.ipynb",
		help="Path to student submission notebook.",
	)
	parser.add_argument(
		"--rubric",
		default="gw08_rubric.json",
		help="Path to rubric JSON file.",
	)
	parser.add_argument(
		"--json-out",
		default="grading_result.json",
		help="Path to structured grading JSON output.",
	)
	parser.add_argument(
		"--md-out",
		default="student_feedback.md",
		help="Path to markdown feedback output.",
	)
	return parser


def main() -> None:
	args = _build_arg_parser().parse_args()

	result = run_autograder(
		assignment_notebook_path=args.assignment,
		submission_notebook_path=args.submission,
		rubric_path=args.rubric,
		json_output_path=args.json_out,
		markdown_output_path=args.md_out,
	)

	print(
		"Autograding complete. "
		f"Score: {result.get('total_score', 0)}/{result.get('max_score', 100)}. "
		f"Saved JSON to {args.json_out} and markdown to {args.md_out}."
	)


if __name__ == "__main__":
	main()
