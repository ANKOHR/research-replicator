"""Config snapshots, recursive diffs, and fixture-only synthetic runs."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io import RepkitError, read_json, write_json
from .schema import HONESTY_BOUNDARY


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def config_id(config: dict[str, Any]) -> str:
    digest = hashlib.sha256(_canonical(config).encode("utf-8")).hexdigest()[:12]
    return f"cfg-{digest}"


def _escape_pointer(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def config_diff(before: Any, after: Any, pointer: str = "") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() - after.keys()):
            changes.append({"op": "remove", "path": f"{pointer}/{_escape_pointer(key)}", "previous": before[key]})
        for key in sorted(after.keys() - before.keys()):
            changes.append({"op": "add", "path": f"{pointer}/{_escape_pointer(key)}", "value": after[key]})
        for key in sorted(before.keys() & after.keys()):
            changes.extend(config_diff(before[key], after[key], f"{pointer}/{_escape_pointer(key)}"))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            changes.append({"op": "replace", "path": pointer or "/", "previous": before, "value": after})
        return changes
    if before != after:
        changes.append({"op": "replace", "path": pointer or "/", "previous": before, "value": after})
    return changes


def _state_path(state_dir: str | Path) -> Path:
    root = Path(state_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def track_config(config_path: str | Path, state_dir: str | Path, reason: str = "manual update") -> dict[str, Any]:
    config = read_json(config_path)
    if not isinstance(config, dict):
        raise RepkitError("A tracked config must be a JSON object.")
    ident = config_id(config)
    root = _state_path(state_dir)
    history_path = root / "config-history.json"
    history = read_json(history_path) if history_path.exists() else {"events": []}
    if not isinstance(history, dict) or not isinstance(history.get("events"), list):
        raise RepkitError(f"Invalid config history at {history_path}.")
    previous_id = history["events"][-1]["config_id"] if history["events"] else None
    previous = read_json(root / "configs" / f"{previous_id}.json") if previous_id else {}
    changes = config_diff(previous, config)
    event = {
        "config_id": ident,
        "parent_config_id": previous_id,
        "timestamp_utc": _timestamp(),
        "reason": reason,
        "changes": changes,
        "honesty": HONESTY_BOUNDARY,
    }
    history["events"].append(event)
    write_json(root / "configs" / f"{ident}.json", config)
    write_json(history_path, history)
    return event


def _load_tracked_config(state_dir: str | Path, ident: str) -> dict[str, Any]:
    if not ident.startswith("cfg-") or any(char not in "0123456789abcdef-" for char in ident[4:]):
        raise RepkitError("Config id has an invalid format.")
    path = Path(state_dir) / "configs" / f"{ident}.json"
    config = read_json(path)
    if not isinstance(config, dict):
        raise RepkitError("Tracked config must be a JSON object.")
    return config


def run_fixture(config_ident: str, repo_dir: str | Path, state_dir: str | Path, script: str = "train.py") -> dict[str, Any]:
    root = Path(repo_dir).resolve()
    manifest_path = root / "repkit-fixture.json"
    if not manifest_path.is_file():
        raise RepkitError("run accepts declared synthetic fixture repos only. Generate one with 'repkit fixtures'.")
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("fixture") is not True or manifest.get("kind") != "synthetic_metric_emitter":
        raise RepkitError("The repo is not marked as a synthetic metric emitter fixture.")
    script_path = (root / script).resolve()
    try:
        script_path.relative_to(root)
    except ValueError as exc:
        raise RepkitError("The fixture script must be inside the fixture repo.") from exc
    if script_path.name != "train.py" or not script_path.is_file():
        raise RepkitError("Only the fixture's train.py metric emitter is supported.")
    script_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()
    if script_hash != manifest.get("script_sha256"):
        raise RepkitError("Fixture script hash does not match its manifest.")

    config = _load_tracked_config(state_dir, config_ident)
    config_path = Path(state_dir) / "configs" / f"{config_ident}.json"
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env["NVIDIA_VISIBLE_DEVICES"] = "void"
    try:
        completed = subprocess.run(
            [sys.executable, str(script_path), "--config", str(config_path)],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip()[:1000]
        raise RepkitError(f"Synthetic metric emitter failed: {detail or exc.returncode}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepkitError("Synthetic metric emitter exceeded the 15 second CPU fixture limit.") from exc
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RepkitError("Fixture script did not return valid JSON metrics.") from exc
    metrics = output.get("metrics") if isinstance(output, dict) else None
    if not isinstance(metrics, list) or any(not isinstance(metric, dict) or "name" not in metric or "value" not in metric for metric in metrics):
        raise RepkitError("Fixture script output must contain a metrics list with name and value fields.")
    record_core = {"config_id": config_ident, "metrics": metrics}
    run_digest = hashlib.sha256(_canonical(record_core).encode("utf-8")).hexdigest()[:12]
    record = {
        "run_id": f"run-{run_digest}",
        **record_core,
        "fixture_repo": root.name,
        "script": script_path.name,
        "timestamp_utc": _timestamp(),
        "execution": "deterministic CPU synthetic metric emitter; no model training",
        "honesty": HONESTY_BOUNDARY,
    }
    root_state = _state_path(state_dir)
    runs_path = root_state / "runs.json"
    runs = read_json(runs_path) if runs_path.exists() else {"runs": []}
    if not isinstance(runs, dict) or not isinstance(runs.get("runs"), list):
        raise RepkitError(f"Invalid run history at {runs_path}.")
    runs["runs"].append(record)
    write_json(runs_path, runs)
    write_json(root_state / "observed.json", record)
    return record
