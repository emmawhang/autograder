"""Extract grading-relevant material from an instructor key notebook."""

from __future__ import annotations

import re
from typing import Any, Dict, List


POINT_PATTERN = re.compile(r"(?:^|[\s(])(\d+(?:\.\d+)?)\s*(?:points?|pts?)\b", re.I)
CRITERIA_PATTERN = re.compile(r"\b(?:grading criteria|rubric|deductions?|partial credit|points?)\b", re.I)


def _points(text: str) -> float | None:
	matches = [float(match.group(1)) for match in POINT_PATTERN.finditer(text)]
	return matches[0] if matches else None


def extract_reference_material(content: Dict[str, Any]) -> Dict[str, Any]:
	sections: List[Dict[str, Any]] = []
	for section in content.get("sections", []):
		text = "\n\n".join(cell["content"] for cell in section.get("cells", []))
		sections.append({
			"title": section.get("title", "Unsectioned content"),
			"content": text,
			"points": _points(text) or _points(section.get("title", "")),
			"has_grading_language": bool(CRITERIA_PATTERN.search(text)),
		})

	explicit_points = [section["points"] for section in sections if section["points"] is not None]
	missing_criteria = not any(section["has_grading_language"] for section in sections)
	missing_points = not explicit_points
	flags: List[str] = []
	if missing_criteria:
		flags.append("Key notebook does not contain explicit grading criteria; instructor review is required.")
	if missing_points:
		flags.append("Key notebook does not contain point allocations; scores cannot be treated as authoritative.")

	return {
		"notebook_path": content.get("path"),
		"sections": sections,
		"has_explicit_criteria": not missing_criteria,
		"has_explicit_points": not missing_points,
		"total_points": sum(explicit_points) if explicit_points else None,
		"flags": flags,
	}
