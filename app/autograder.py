"""CLI compatibility wrapper for the modular notebook grader."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from grading import (
	attach_reference_flags,
	build_grading_prompt,
	call_llm,
	markdown_feedback,
	parse_llm_json,
)
from notebook_parser import extract_notebook_content


def load_rubric(path: str) -> Dict[str, Any]:
	with open(path, "r", encoding="utf-8") as file:
		return json.load(file)


def save_json(result: Dict[str, Any], output_path: str) -> None:
	with open(output_path, "w", encoding="utf-8") as file:
		json.dump(result, file, indent=2, ensure_ascii=False)


def save_markdown_feedback(result: Dict[str, Any], output_path: str) -> None:
	with open(output_path, "w", encoding="utf-8") as file:
		file.write(markdown_feedback(result))


def run_autograder(
	key_notebook_path: str,
	submission_notebook_path: str,
	json_output_path: str,
	markdown_output_path: str,
	rubric_path: str | None = None,
	assignment_notebook_path: str | None = None,
) -> Dict[str, Any]:
	key_path = key_notebook_path or assignment_notebook_path
	if not key_path:
		raise ValueError("An instructor key notebook is required.")
	key_content = extract_notebook_content(key_path)
	submission_content = extract_notebook_content(submission_notebook_path)
	rubric = load_rubric(rubric_path) if rubric_path else None
	result = attach_reference_flags(
		parse_llm_json(call_llm(build_grading_prompt(key_content, submission_content, rubric))),
		key_content,
	)
	save_json(result, json_output_path)
	save_markdown_feedback(result, markdown_output_path)
	return result


def _build_arg_parser() -> argparse.ArgumentParser:
	root = Path(__file__).resolve().parents[1]
	parser = argparse.ArgumentParser(description="Key-notebook-driven LLM autograder.")
	parser.add_argument("--key", "--assignment", dest="key", required=True,
		help="Instructor answer-key notebook (.ipynb).")
	parser.add_argument("--submission", required=True, help="Student notebook (.ipynb).")
	parser.add_argument("--rubric", default=None, help="Optional supplemental rubric JSON.")
	parser.add_argument("--json-out", default="grading_result.json")
	parser.add_argument("--md-out", default="student_feedback.md")
	parser.set_defaults(_root=root)
	return parser


def main() -> None:
	args = _build_arg_parser().parse_args()
	result = run_autograder(
		key_notebook_path=args.key,
		submission_notebook_path=args.submission,
		rubric_path=args.rubric,
		json_output_path=args.json_out,
		markdown_output_path=args.md_out,
	)
	print(f"Autograding complete. Score: {result.get('total_score', 0)}/{result.get('max_score', 0)}.")


if __name__ == "__main__":
	main()
