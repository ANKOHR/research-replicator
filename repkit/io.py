"""Deterministic file and JSON helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class RepkitError(Exception):
    """An expected user-facing error."""


def read_json(path: str | Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise RepkitError(f"Cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RepkitError(f"Invalid JSON in {path}: {exc}") from exc


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json_text(value), encoding="utf-8", newline="\n")


def write_text(path: str | Path, value: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8", newline="\n")
