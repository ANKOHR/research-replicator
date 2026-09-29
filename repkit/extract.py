"""Structure-aware extraction for the documented synthetic Markdown format."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import RepkitError
from .schema import HYPERPARAMETER_FIELDS, UNKNOWN, SetupRecord, SourcedValue


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    line: int
    end: int

    @property
    def label(self) -> str:
        return self.title.strip()


def _headings(lines: list[str]) -> list[Heading]:
    raw: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            raw.append((len(match.group(1)), match.group(2).strip(), i))
    output = []
    for index, (level, title, line) in enumerate(raw):
        end = len(lines)
        for next_level, _, next_line in raw[index + 1:]:
            if next_level <= level:
                end = next_line
                break
        output.append(Heading(level, title, line, end))
    return output


def _section_body(lines: list[str], heading: Heading) -> str:
    start = heading.line + 1
    children = [h.line for h in _headings(lines) if h.line > heading.line and h.level > heading.level and h.line < heading.end]
    end = min(children) if children else heading.end
    return "\n".join(lines[start:end])


def _groups(lines: list[str], root: Heading) -> dict[str, list[tuple[Heading, str]]]:
    names: dict[str, list[tuple[Heading, str]]] = {
        "datasets": [], "model": [], "hyperparameters": [], "metrics": [], "results": []
    }
    aliases = {
        "datasets": ("dataset",),
        "model": ("model", "architecture"),
        "hyperparameters": ("hyperparameter", "parameters", "settings"),
        "metrics": ("metrics", "evaluation metrics"),
        "results": ("reported results", "results", "quantitative results"),
    }
    for heading in _headings(lines):
        if not (root.line < heading.line < root.end) or heading.level <= root.level:
            continue
        normalized = heading.title.lower().strip()
        for key, terms in aliases.items():
            if any(term in normalized for term in terms):
                names[key].append((heading, _section_body(lines, heading)))
                break
    return names


def _normalize_key(key: str) -> str:
    key = key.strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "", key)


def _value(raw: str) -> Any:
    text = raw.strip().strip("`*_ ")
    text = re.sub(r"\s+\([^)]*\)\s*$", "", text)
    if not text:
        return ""
    low = text.lower()
    if low in {"true", "false"}:
        return low == "true"
    numeric = text.replace(",", "")
    if re.fullmatch(r"[-+]?\d+", numeric):
        try:
            return int(numeric)
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?|[-+]?\d+[eE][-+]?\d+", numeric):
        try:
            return float(numeric)
        except ValueError:
            pass
    return text


def _key_values(body: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for line in body.splitlines():
        match = re.match(r"\s*(?:[-*+]\s*)?([A-Za-z][A-Za-z0-9 _-]*)\s*:\s*(.*?)\s*$", line)
        if match:
            values[_normalize_key(match.group(1))] = _value(match.group(2))
    return values


def _table_rows(body: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    lines = body.splitlines()
    for index, line in enumerate(lines[:-1]):
        if "|" not in line or not re.search(r"\|\s*:?-{3,}", lines[index + 1]):
            continue
        headers = [_normalize_key(part) for part in line.strip().strip("|").split("|")]
        for data_line in lines[index + 2:]:
            if "|" not in data_line:
                break
            cells = [cell.strip() for cell in data_line.strip().strip("|").split("|")]
            if len(cells) != len(headers):
                continue
            rows.append({header: _value(cell) for header, cell in zip(headers, cells)})
    return rows


def _field_source(heading: Heading) -> str:
    return heading.label


def _field(rows: list[tuple[Heading, str]], aliases: tuple[str, ...]) -> SourcedValue | dict[str, Any]:
    for heading, body in rows:
        values = _key_values(body)
        for alias in aliases:
            key = _normalize_key(alias)
            if key in values:
                return SourcedValue(values[key], _field_source(heading))
        for row in _table_rows(body):
            for alias in aliases:
                key = _normalize_key(alias)
                if key in row and row[key] not in (None, ""):
                    return SourcedValue(row[key], _field_source(heading))
    return UNKNOWN.copy()


def extract_text(markdown: str) -> dict[str, Any]:
    lines = markdown.splitlines()
    headings = _headings(lines)
    title_heading = next((heading for heading in headings if heading.level == 1), None)
    title = SourcedValue(title_heading.title, "Document title") if title_heading else UNKNOWN.copy()
    root = next((heading for heading in headings if heading.title.strip().lower() in {"experimental setup", "experiments", "experimental details"}), None)
    if root is None:
        groups = {key: [] for key in ("datasets", "model", "hyperparameters", "metrics", "results")}
        status = "UNKNOWN"
        root_label = None
    else:
        groups = _groups(lines, root)
        status = "PRESENT"
        root_label = root.label

    datasets: list[dict[str, Any]] = []
    for heading, body in groups["datasets"]:
        values = _key_values(body)
        for row in _table_rows(body):
            values.update(row)
        if "name" in values:
            datasets.append({"name": values["name"], "source_section": _field_source(heading)})
        else:
            for line in body.splitlines():
                match = re.match(r"\s*[-*+]\s+([^:|]+?)\s*$", line)
                if match:
                    name = _value(match.group(1))
                    datasets.append({"name": name, "source_section": _field_source(heading)})

    architecture = _field(groups["model"], ("architecture", "model", "name"))

    hparam_rows = groups["hyperparameters"]
    aliases = {
        "learning_rate": ("learning_rate", "learning rate", "lr"),
        "batch_size": ("batch_size", "batch size"),
        "epochs": ("epochs", "epoch_count", "num_epochs"),
        "seed": ("seed", "random_seed"),
        "optimizer": ("optimizer", "optimiser"),
    }
    hyperparameters = {
        name: _field(hparam_rows, candidates) for name, candidates in aliases.items()
    }

    metric_rows: list[dict[str, Any]] = []
    metric_tolerances: dict[str, tuple[Any, str]] = {}
    for heading, body in groups["metrics"]:
        for row in _table_rows(body):
            name = row.get("metric", row.get("name"))
            if name is None:
                continue
            metric = {
                "name": name,
                "unit": row.get("unit", "UNKNOWN"),
                "source_section": _field_source(heading),
                "tolerance": row.get("tolerance", UNKNOWN.copy()),
                "tolerance_source_section": _field_source(heading) if "tolerance" in row else None,
            }
            if "tolerance" in row:
                metric_tolerances[str(name)] = (row["tolerance"], _field_source(heading))
            else:
                metric_tolerances[str(name)] = (UNKNOWN.copy(), None)
            metric_rows.append(metric)
        for line in body.splitlines():
            match = re.match(r"\s*[-*+]\s+([^:]+?)\s*:\s*(.*)$", line)
            if match:
                details = _key_values(match.group(2))
                metric_rows.append({"name": _value(match.group(1)), "unit": details.get("unit", "UNKNOWN"), "source_section": _field_source(heading)})

    reported: list[dict[str, Any]] = []
    for heading, body in groups["results"]:
        for row in _table_rows(body):
            name = row.get("metric", row.get("name"))
            if name is None or "value" not in row:
                continue
            result = {
                "metric": name,
                "value": row["value"],
                "unit": row.get("unit", "UNKNOWN"),
                "source_section": _field_source(heading),
            }
            if "tolerance" in row:
                result["tolerance"] = row["tolerance"]
                result["tolerance_source_section"] = _field_source(heading)
            elif str(name) in metric_tolerances:
                result["tolerance"], result["tolerance_source_section"] = metric_tolerances[str(name)]
            else:
                result["tolerance"] = UNKNOWN.copy()
                result["tolerance_source_section"] = None
            reported.append(result)

    return SetupRecord(
        schema_version="1.0",
        title=title,
        experiments_status=status,
        experiments_source_section=root_label,
        datasets=datasets,
        architecture=architecture,
        hyperparameters=hyperparameters,
        metrics=metric_rows,
        reported_results=reported,
    ).as_dict()


def extract_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise RepkitError(f"Cannot read paper {source}: {exc}") from exc
    return extract_text(text)
