"""Notebook loading and lightweight question/answer extraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import nbformat


class NotebookParseError(ValueError):
	"""Raised when an uploaded notebook cannot be parsed safely."""


def load_notebook(path: str) -> nbformat.NotebookNode:
	try:
		with open(path, "r", encoding="utf-8") as file:
			return nbformat.read(file, as_version=4)
	except (OSError, ValueError, TypeError) as exc:
		raise NotebookParseError(f"Could not parse notebook '{Path(path).name}': {exc}") from exc


def _text(value: Any) -> str:
	if isinstance(value, list):
		return "".join(str(item) for item in value)
	return str(value or "")


def _extract_cell_output_text(outputs: List[Dict[str, Any]]) -> str:
	extracted: List[str] = []
	for output in outputs or []:
		output_type = output.get("output_type", "")
		if output_type == "stream":
			extracted.append(_text(output.get("text", "")))
		elif output_type in {"execute_result", "display_data"}:
			data = output.get("data", {})
			if "text/plain" in data:
				extracted.append(_text(data["text/plain"]))
		elif output_type == "error":
			extracted.append(
				f"{output.get('ename', 'Error')}: {output.get('evalue', '')}\n"
				+ "\n".join(output.get("traceback", []))
			)
	return "\n".join(part.strip() for part in extracted if part.strip()).strip()


def _is_question_heading(text: str) -> bool:
	return bool(re.search(r"\b(?:question|problem|task|part)\s*\d+", text, re.I))


def extract_notebook_content(path: str) -> Dict[str, Any]:
	notebook = load_notebook(path)
	markdown_cells: List[str] = []
	code_cells: List[str] = []
	outputs: List[str] = []
	all_cells: List[str] = []
	sections: List[Dict[str, Any]] = []
	current: Dict[str, Any] | None = None

	for index, cell in enumerate(notebook.cells, start=1):
		source = _text(cell.get("source", "")).strip()
		cell_type = cell.get("cell_type")
		if cell_type == "markdown":
			markdown_cells.append(source)
			all_cells.append(f"[Markdown Cell {index}]\n{source}".strip())
			if source and (_is_question_heading(source) or source.startswith("#")):
				current = {"title": source, "cells": []}
				sections.append(current)
		elif cell_type == "code":
			code_cells.append(source)
			all_cells.append(f"[Code Cell {index}]\n{source}".strip())
			if current is None:
				current = {"title": "Unsectioned content", "cells": []}
				sections.append(current)
			current["cells"].append({"cell": index, "type": "code", "content": source})
			output_text = _extract_cell_output_text(cell.get("outputs", []))
			if output_text:
				outputs.append(f"[Outputs Cell {index}]\n{output_text}")
				current["cells"].append({"cell": index, "type": "output", "content": output_text})
		elif cell_type:
			all_cells.append(f"[{cell_type.title()} Cell {index}]\n{source}".strip())

		if cell_type == "markdown" and current is not None:
			current["cells"].append({"cell": index, "type": "markdown", "content": source})

	return {
		"path": path,
		"num_cells": len(notebook.cells),
		"markdown_cells": markdown_cells,
		"code_cells": code_cells,
		"outputs": outputs,
		"sections": sections,
		"prompt_text": "\n\n".join(all_cells + outputs).strip(),
	}
