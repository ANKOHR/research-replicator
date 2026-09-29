from __future__ import annotations

from repkit.compare import compare_records
from repkit.extract import extract_file
from repkit.fixtures import create_fixtures
from repkit.io import write_json
from repkit.plan import build_plan
from repkit.report import render_html, render_markdown
from repkit.tracker import run_fixture, track_config


def test_fixture_generation_is_byte_deterministic(tmp_path):
    left = create_fixtures(tmp_path / "left")
    right = create_fixtures(tmp_path / "right")
    assert len(left) == len(right)
    from pathlib import Path
    assert [Path(path).read_bytes() for path in left] == [Path(path).read_bytes() for path in right]


def test_end_to_end_extract_plan_track_run_compare_report(fixture_files, tmp_path):
    state = tmp_path / "workflow"
    setup = extract_file(fixture_files["paper"])
    write_json(state / "setup.json", setup)
    write_json(state / "plan.json", build_plan(setup))
    tracked = track_config(fixture_files["config"], state, "fixture baseline")
    observed = run_fixture(tracked["config_id"], fixture_files["repo"], state)
    comparison = compare_records(setup, observed)
    write_json(state / "comparison.json", comparison)
    assert comparison["overall_status"] == "PASS"

    markdown = render_markdown(state)
    for expected in ("Setup Record", "Reproduction Plan", "Config History", "Comparison Table", "Provenance", "HONESTY BOUNDARY", "accuracy", tracked["config_id"]):
        assert expected in markdown
    html = render_html(state)
    assert "class=\"honesty\"" in html
    assert "HONESTY BOUNDARY" in html
    assert "Reported" in html and "Observed" in html


def test_report_without_state_still_discloses_boundary(tmp_path):
    report = render_markdown(tmp_path / "empty")
    assert "no training runs, no real papers, and no real models" in report
    assert "UNKNOWN" in report
