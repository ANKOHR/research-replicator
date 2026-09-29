from __future__ import annotations

from repkit.io import json_text
from repkit.extract import extract_file
from repkit.plan import build_plan


def _resolve(pointer: str, record: dict):
    current = record
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def test_plan_is_ordered_and_references_only_extracted_fields(fixture_files):
    setup = extract_file(fixture_files["paper"])
    plan = build_plan(setup)
    assert [step["order"] for step in plan["steps"]] == list(range(1, 7))
    assert all(step["field_refs"] for step in plan["steps"])
    for step in plan["steps"]:
        for pointer in step["field_refs"]:
            _resolve(pointer, setup)
        assert step["expected_observations"]
        assert step["falsifiable_checkpoint"]


def test_plan_marks_missing_setup_and_hyperparameters_unknown(fixture_files):
    setup = extract_file(fixture_files["empty_paper"])
    plan = build_plan(setup)
    assert plan["steps"][0]["expected_observations"]["status"] == "UNKNOWN"
    assert plan["steps"][1]["expected_observations"]["datasets"] == "UNKNOWN"
    assert set(plan["steps"][3]["expected_observations"].values()) == {"UNKNOWN"}
    assert plan["steps"][4]["expected_observations"]["reported_results"] == "UNKNOWN"


def test_plan_missing_hyperparameter_sections_mark_unknown(fixture_files):
    plan = build_plan(extract_file(fixture_files["missing_hparams"]))
    assert plan["steps"][3]["expected_observations"]["learning_rate"] == "UNKNOWN"


def test_plan_reruns_are_byte_identical(fixture_files):
    first = build_plan(extract_file(fixture_files["paper"]))
    second = build_plan(extract_file(fixture_files["paper"]))
    assert json_text(first).encode() == json_text(second).encode()
