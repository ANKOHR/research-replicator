"""Markdown and HTML report assembly from stored provenance artifacts."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from .io import read_json
from .schema import HONESTY_BOUNDARY


HONESTY_BANNER = f"HONESTY BOUNDARY: {HONESTY_BOUNDARY}"


def _optional_json(path: Path, default: Any) -> Any:
    return read_json(path) if path.exists() else default


def _comparison_table(comparison: dict[str, Any] | None) -> str:
    lines = ["| Metric | Reported | Observed | Unit | Tolerance | Difference | Status |", "| --- | ---: | ---: | --- | ---: | ---: | --- |"]
    if not comparison or not comparison.get("metrics"):
        lines.append("| None | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | No comparison stored |")
    else:
        for row in comparison["metrics"]:
            lines.append("| {metric} | {reported} | {observed} | {unit} | {tolerance} | {difference} | {status} |".format(
                metric=row.get("metric", "UNKNOWN"),
                reported=row.get("reported", "UNKNOWN"),
                observed=row.get("observed", "UNKNOWN"),
                unit=row.get("unit", "UNKNOWN"),
                tolerance=row.get("tolerance", "UNKNOWN"),
                difference=row.get("difference", "UNKNOWN"),
                status=row.get("status", "UNKNOWN"),
            ))
    return "\n".join(lines)


def render_markdown(state_dir: str | Path) -> str:
    root = Path(state_dir)
    setup = _optional_json(root / "setup.json", {})
    plan = _optional_json(root / "plan.json", {})
    history = _optional_json(root / "config-history.json", {"events": []})
    runs = _optional_json(root / "runs.json", {"runs": []})
    comparison = _optional_json(root / "comparison.json", None)
    setup_text = __import__("json").dumps(setup, ensure_ascii=False, indent=2, sort_keys=True)
    plan_text = __import__("json").dumps(plan, ensure_ascii=False, indent=2, sort_keys=True)
    history_text = __import__("json").dumps(history, ensure_ascii=False, indent=2, sort_keys=True)
    provenance = [
        f"- setup schema: {setup.get('schema_version', 'UNKNOWN')}",
        f"- plan version: {plan.get('plan_version', 'UNKNOWN')}",
        f"- tracked config events: {len(history.get('events', []))}",
        f"- synthetic fixture runs: {len(runs.get('runs', []))}",
        f"- comparison config id: {(comparison or {}).get('config_id', 'UNKNOWN')}",
        "- execution boundary: hash-pinned fixture metric emitter, CPU environment, no model training",
    ]
    sections = [
        "# ResearchReplicator Report",
        "",
        f"> {HONESTY_BANNER}",
        "",
        "## Setup Record",
        "",
        "```json",
        setup_text,
        "```",
        "",
        "## Reproduction Plan",
        "",
        "```json",
        plan_text,
        "```",
        "",
        "## Config History",
        "",
        "```json",
        history_text,
        "```",
        "",
        "## Comparison Table",
        "",
        _comparison_table(comparison),
        "",
        "## Provenance",
        "",
        *provenance,
        "",
    ]
    return "\n".join(sections)


def render_html(state_dir: str | Path) -> str:
    markdown = render_markdown(state_dir)
    parts = markdown.split("\n")
    banner = html.escape(HONESTY_BANNER)
    title = html.escape(parts[0].removeprefix("# "))
    body = html.escape(markdown)
    return (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{title}</title><style>body{{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}}"
        ".honesty{border:2px solid #9b2c2c;background:#fff5f5;padding:1rem;font-weight:700}"
        "pre{white-space:pre-wrap;background:#f6f8fa;padding:1rem}</style></head><body>"
        f"<div class=\"honesty\">{banner}</div><h1>{title}</h1><pre>{body}</pre>"
        "</body></html>\n"
    )
