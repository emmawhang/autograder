"""Prompt construction, LLM integration, and grading-result validation."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

from reference_extractor import extract_reference_material


REQUIRED_OUTPUT_SCHEMA: Dict[str, Any] = {
	"total_score": 0,
	"max_score": 100,
	"question_scores": [
		{
			"question": "string",
			"score": 0,
			"max_score": 0,
			"deductions": ["string"],
			"feedback": "string",
		}
	],
	"breakdown": [],
	"final_feedback": "string",
	"flags_for_manual_review": ["string"],
}


def build_grading_prompt(
	key_content: Dict[str, Any],
	submission_content: Dict[str, Any],
	supplemental_rubric: Dict[str, Any] | None = None,
) -> str:
	reference = extract_reference_material(key_content)
	rubric_text = json.dumps(supplemental_rubric, indent=2) if supplemental_rubric else "None supplied."
	reference_text = json.dumps(reference, indent=2)
	return f"""You are grading a student notebook against an instructor answer-key notebook.
Use the key notebook as the primary authority. Compare corresponding questions and answers.
Accept equivalent correct methods, formulas, variable names, and explanations when they satisfy
the key's intended result. Award partial credit only for demonstrated progress. Do not invent
point allocations: if the key lacks points, flag the question for instructor review and use
max_score 0 for that question unless an explicitly supplied supplemental rubric provides it.
Do not treat code comments alone as evidence that an implementation works. Explain every
deduction concisely. Return valid JSON only, with no markdown fences.

OUTPUT SCHEMA:
{json.dumps(REQUIRED_OUTPUT_SCHEMA, indent=2)}

REFERENCE EXTRACTION:
{reference_text}

SUPPLEMENTAL RUBRIC (optional):
{rubric_text}

INSTRUCTOR KEY NOTEBOOK:
{key_content["prompt_text"]}

STUDENT NOTEBOOK:
{submission_content["prompt_text"]}
"""


def call_llm(prompt: str) -> str:
	load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
	provider = os.getenv("LLM_PROVIDER", "").strip().lower()
	anthropic_key = (os.getenv("ANTHROPIC_API_KEY", "").strip()
		or os.getenv("CLAUDE_API_KEY", "").strip())
	model_name = os.getenv("MODEL_NAME", "").strip()

	if provider == "anthropic" or (not provider and anthropic_key):
		if not anthropic_key:
			raise ValueError("LLM_PROVIDER=anthropic requires ANTHROPIC_API_KEY in .env.")
		client = Anthropic(api_key=anthropic_key)
		response = client.messages.create(
			model=model_name or "claude-sonnet-5",
			max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
			thinking={"type": "disabled"},
			system="You are a strict grading assistant. Return valid JSON only.",
			messages=[{"role": "user", "content": prompt}],
		)
		content = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
		if not content:
			raise ValueError("LLM returned empty content.")
		return content

	api_key = (os.getenv("GROQ_API_KEY", "").strip()
		or os.getenv("OPENAI_API_KEY", "").strip()
		or os.getenv("GROK_API_KEY", "").strip())
	if not api_key or not model_name:
		raise ValueError("Missing API key or MODEL_NAME. Configure the provider in .env.")
	base_url = (os.getenv("GROQ_BASE_URL", "").strip()
		or os.getenv("OPENAI_BASE_URL", "").strip()
		or os.getenv("GROK_BASE_URL", "").strip())
	if not base_url and os.getenv("GROQ_API_KEY"):
		base_url = "https://api.groq.com/openai/v1"
	client_kwargs: Dict[str, Any] = {"api_key": api_key}
	if base_url:
		client_kwargs["base_url"] = base_url
	response = OpenAI(**client_kwargs).chat.completions.create(
		model=model_name,
		messages=[
			{"role": "system", "content": "Return valid JSON only."},
			{"role": "user", "content": prompt},
		],
		temperature=0,
	)
	if response.choices[0].message.content is None:
		raise ValueError("LLM returned empty content.")
	return response.choices[0].message.content


def parse_llm_json(response: str) -> Dict[str, Any]:
	cleaned = response.strip()
	if cleaned.startswith("```"):
		lines = cleaned.splitlines()
		cleaned = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()
	try:
		parsed = json.loads(cleaned)
	except json.JSONDecodeError as exc:
		raise ValueError(f"Failed to parse LLM JSON response: {exc}") from exc
	required = {"total_score", "max_score", "breakdown", "final_feedback", "flags_for_manual_review"}
	missing = required - set(parsed)
	if missing:
		raise ValueError(f"LLM JSON is missing required keys: {sorted(missing)}")
	if not isinstance(parsed["breakdown"], list):
		raise ValueError("LLM JSON field 'breakdown' must be a list.")
	return parsed


def attach_reference_flags(result: Dict[str, Any], key_content: Dict[str, Any]) -> Dict[str, Any]:
	"""Ensure missing key metadata is visible even if the model omits the flag."""
	reference_flags = extract_reference_material(key_content)["flags"]
	existing = [str(flag) for flag in result.get("flags_for_manual_review", [])]
	result["flags_for_manual_review"] = list(dict.fromkeys(existing + reference_flags))
	return result


def markdown_feedback(result: Dict[str, Any]) -> str:
	lines = [
		"# Autograder Feedback",
		"",
		f"## Score: {result.get('total_score', 0)}/{result.get('max_score', 0)}",
		"",
		"## Question-level breakdown",
		"",
	]
	for item in result.get("question_scores") or result.get("breakdown", []):
		lines.append(f"- **{item.get('question', item.get('criterion', 'Unknown'))}**: "
			+ f"{item.get('score', 0)}/{item.get('max_score', 0)}")
		feedback = item.get("feedback", item.get("reason", ""))
		if feedback:
			lines.append(f"  - {feedback}")
	lines.extend(["", "## Final Feedback", "", result.get("final_feedback", "No feedback provided."), "",
		"## Flags For Manual Review", ""])
	lines.extend(f"- {flag}" for flag in result.get("flags_for_manual_review", []) or ["None"])
	return "\n".join(lines).rstrip() + "\n"


def plain_text_feedback(result: Dict[str, Any]) -> str:
	"""Create concise feedback suitable for Brightspace Overall Feedback."""
	lines = [
		f"Score: {result.get('total_score', 0)}/{result.get('max_score', 0)}",
		"",
		"Question-level results:",
	]
	items = result.get("question_scores") or result.get("breakdown", [])
	for item in items:
		name = item.get("question", item.get("criterion", "Question"))
		score = item.get("score", 0)
		max_score = item.get("max_score", 0)
		lines.append(f"- {name}: {score}/{max_score}")
		deductions = item.get("deductions") or []
		if deductions:
			lines.extend(f"  Deduction: {deduction}" for deduction in deductions)
		explanation = item.get("feedback", item.get("reason", "")).strip()
		if explanation:
			lines.append(f"  Explanation: {explanation}")
	lines.extend(["", "Overall feedback:", result.get("final_feedback", "No feedback provided.")])
	flags = result.get("flags_for_manual_review") or []
	if flags:
		lines.extend(["", "Instructor review flags:"])
		lines.extend(f"- {flag}" for flag in flags)
	return "\n".join(lines).strip() + "\n"
