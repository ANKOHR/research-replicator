from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(*arguments: str, cwd: Path):
    return subprocess.run([sys.executable, "-m", "repkit", *arguments], cwd=cwd, check=True, capture_output=True, text=True)


def test_cli_help_states_honesty_boundary(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = _run("--help", cwd=root)
    assert "no real papers" in result.stdout
    assert "no training runs" in result.stdout


def test_cli_smoke_for_each_subcommand(tmp_path):
    root = Path(__file__).resolve().parents[1]
    fixtures = tmp_path / "fixtures"
    state = tmp_path / "state"
    state.mkdir()
    _run("fixtures", "--out", str(fixtures), cwd=root)
    setup_path = tmp_path / "setup.json"
    _run("extract", str(fixtures / "toy-paper.md"), "--out", str(setup_path), "--state-dir", str(state), cwd=root)
    plan_path = tmp_path / "plan.json"
    _run("plan", str(setup_path), "--out", str(plan_path), "--state-dir", str(state), cwd=root)
    tracked = _run("track", "--config", str(fixtures / "synthetic-repo" / "config.json"), "--state-dir", str(state), cwd=root)
    config_id = json.loads(tracked.stdout)["config_id"]
    run = _run("run", "--config", config_id, "--repo", str(fixtures / "synthetic-repo"), "--state-dir", str(state), cwd=root)
    observed_path = tmp_path / "observed.json"
    observed_path.write_text(run.stdout, encoding="utf-8")
    comparison_path = tmp_path / "comparison.json"
    _run("compare", str(setup_path), str(observed_path), "--out", str(comparison_path), "--state-dir", str(state), cwd=root)
    assert json.loads(comparison_path.read_text(encoding="utf-8"))["overall_status"] == "PASS"
    _run("report", "--format", "md", "--state-dir", str(state), cwd=root)
    assert (state / "report.md").is_file()
    _run("report", "--format", "html", "--state-dir", str(state), cwd=root)
    assert (state / "report.html").is_file()


def test_run_help_explains_cpu_metric_emitter_boundary(tmp_path):
    root = Path(__file__).resolve().parents[1]
    result = _run("run", "--help", cwd=root)
    assert "does not train a model" in result.stdout
    assert "hash-pinned deterministic CPU metric emitter" in result.stdout
