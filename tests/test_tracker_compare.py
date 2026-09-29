from __future__ import annotations

import json

import pytest

from repkit.compare import compare_records
from repkit.extract import extract_file
from repkit.io import RepkitError, json_text, write_json
from repkit.tracker import run_fixture, track_config


def test_config_edits_create_correct_diffs_and_run_keeps_config_id(fixture_files, tmp_path):
    state = tmp_path / "state"
    first = track_config(fixture_files["config"], state, "baseline")
    assert first["parent_config_id"] is None
    assert {item["path"] for item in first["changes"]} == {
        "/learning_rate", "/batch_size", "/epochs", "/seed", "/optimizer"
    }
    edited = json.loads(fixture_files["config"].read_text(encoding="utf-8"))
    edited["learning_rate"] = 0.2
    edited["batch_size"] = 24
    config_path = tmp_path / "edited.json"
    write_json(config_path, edited)
    second = track_config(config_path, state, "increase rate and batch")
    assert second["parent_config_id"] == first["config_id"]
    assert second["changes"] == [
        {"op": "replace", "path": "/batch_size", "previous": 16, "value": 24},
        {"op": "replace", "path": "/learning_rate", "previous": 0.1, "value": 0.2},
    ]
    run = run_fixture(second["config_id"], fixture_files["repo"], state)
    assert run["config_id"] == second["config_id"]
    assert run["execution"].startswith("deterministic CPU synthetic metric emitter")
    assert run["metrics"] == [
        {"name": "accuracy", "value": 0.77, "unit": "fraction"},
        {"name": "loss", "value": 0.23, "unit": "toy-loss-units"},
    ]


def test_run_rejects_unmarked_repo(fixture_files, tmp_path):
    state = tmp_path / "state"
    tracked = track_config(fixture_files["config"], state)
    with pytest.raises(RepkitError, match="synthetic fixture repos only"):
        run_fixture(tracked["config_id"], tmp_path, state)


def test_comparator_flags_out_of_tolerance_with_reported_and_observed_values(fixture_files):
    setup = extract_file(fixture_files["paper"])
    observed = {"config_id": "cfg-example", "metrics": [
        {"name": "accuracy", "value": 0.70, "unit": "fraction"},
        {"name": "loss", "value": 0.24, "unit": "toy-loss-units"},
    ]}
    comparison = compare_records(setup, observed)
    accuracy = next(row for row in comparison["metrics"] if row["metric"] == "accuracy")
    assert comparison["overall_status"] == "FAIL"
    assert accuracy["reported"] == 0.77
    assert accuracy["observed"] == 0.70
    assert accuracy["unit"] == "fraction"
    assert accuracy["status"] == "OUT_OF_TOLERANCE"


def test_comparator_accepts_in_tolerance_synthetic_observations(fixture_files):
    setup = extract_file(fixture_files["paper"])
    observed = {"metrics": [
        {"name": "accuracy", "value": 0.765, "unit": "fraction"},
        {"name": "loss", "value": 0.24, "unit": "toy-loss-units"},
    ]}
    result = compare_records(setup, observed)
    assert result["overall_status"] == "PASS"
    assert [row["status"] for row in result["metrics"]] == ["PASS", "PASS"]


def test_comparator_marks_unknown_tolerance_incomplete(fixture_files):
    setup = extract_file(fixture_files["paper"])
    setup["reported_results"][0].pop("tolerance")
    setup["reported_results"] = setup["reported_results"][:1]
    observed = {"metrics": [{"name": "accuracy", "value": 0.77, "unit": "fraction"}]}
    result = compare_records(setup, observed)
    accuracy = next(row for row in result["metrics"] if row["metric"] == "accuracy")
    assert accuracy["status"] == "TOLERANCE_UNKNOWN"
    assert result["overall_status"] == "INCOMPLETE"


def test_extraction_and_comparison_reruns_are_byte_identical(fixture_files):
    first = extract_file(fixture_files["paper"])
    second = extract_file(fixture_files["paper"])
    assert json_text(first).encode() == json_text(second).encode()
    observed = {"metrics": [
        {"name": "accuracy", "value": 0.765, "unit": "fraction"},
        {"name": "loss", "value": 0.24, "unit": "toy-loss-units"},
    ]}
    one = compare_records(first, observed)
    two = compare_records(second, observed)
    assert json_text(one).encode() == json_text(two).encode()
