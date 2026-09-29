"""Build an ordered, falsifiable plan solely from extracted setup fields."""

from __future__ import annotations

from typing import Any

from .schema import HONESTY_BOUNDARY


def _known(value: Any) -> bool:
    return isinstance(value, dict) and "value" in value


def _observed(value: Any) -> Any:
    return value.get("value") if _known(value) else "UNKNOWN"


def build_plan(setup: dict[str, Any]) -> dict[str, Any]:
    hparams = setup.get("hyperparameters", {})
    hparam_names = ("learning_rate", "batch_size", "epochs", "seed", "optimizer")
    hparam_refs = [f"/hyperparameters/{key}" for key in hparam_names]
    steps = [
        {
            "order": 1,
            "id": "confirm_experimental_section",
            "action": "Confirm whether an experimental setup section was declared.",
            "field_refs": ["/sections/experiments"],
            "expected_observations": {"status": setup.get("sections", {}).get("experiments", {}).get("status", "UNKNOWN")},
            "controls": {"source_section": setup.get("sections", {}).get("experiments", {}).get("source_section") or "UNKNOWN"},
            "falsifiable_checkpoint": "The extracted section status is PRESENT or UNKNOWN.",
        },
        {
            "order": 2,
            "id": "inspect_declared_datasets",
            "action": "Record the dataset names declared in the setup.",
            "field_refs": ["/datasets"],
            "expected_observations": {"datasets": setup.get("datasets", []) if setup.get("sections", {}).get("experiments", {}).get("status") == "PRESENT" else "UNKNOWN"},
            "controls": {"source": "extracted setup record"},
            "falsifiable_checkpoint": "Every listed dataset has a source section, or the dataset field is UNKNOWN.",
        },
        {
            "order": 3,
            "id": "record_declared_model",
            "action": "Record the model architecture stated in the setup.",
            "field_refs": ["/model/architecture"],
            "expected_observations": {"architecture": _observed(setup.get("model", {}).get("architecture", {}))},
            "controls": {"architecture_source": setup.get("model", {}).get("architecture", {}).get("source_section", "UNKNOWN")},
            "falsifiable_checkpoint": "The extracted architecture value matches its cited source, or is UNKNOWN.",
        },
        {
            "order": 4,
            "id": "record_declared_hyperparameters",
            "action": "Use only hyperparameter values declared in the setup record.",
            "field_refs": hparam_refs,
            "expected_observations": {key: _observed(hparams.get(key, {})) for key in hparam_names},
            "controls": {"seed": _observed(hparams.get("seed", {}))},
            "falsifiable_checkpoint": "Each parameter is cited or marked UNKNOWN before a run is considered.",
        },
        {
            "order": 5,
            "id": "record_declared_metrics_and_targets",
            "action": "Record metric names, units, tolerances, and reported targets from the setup.",
            "field_refs": ["/metrics", "/reported_results"],
            "expected_observations": {
                "metrics": setup.get("metrics", []) if setup.get("sections", {}).get("experiments", {}).get("status") == "PRESENT" else "UNKNOWN",
                "reported_results": setup.get("reported_results", []) if setup.get("sections", {}).get("experiments", {}).get("status") == "PRESENT" else "UNKNOWN",
            },
            "controls": {"tolerance_policy": "Use declared per-metric tolerances; UNKNOWN is not a pass."},
            "falsifiable_checkpoint": "Every comparison target and tolerance is extracted, or explicitly UNKNOWN.",
        },
        {
            "order": 6,
            "id": "emit_synthetic_cpu_observations",
            "action": "For a declared fixture repo only, run its deterministic CPU metric emitter.",
            "field_refs": hparam_refs + ["/metrics", "/reported_results"],
            "expected_observations": {"reported_results": setup.get("reported_results", []) if setup.get("sections", {}).get("experiments", {}).get("status") == "PRESENT" else "UNKNOWN"},
            "controls": {"training": "none", "seed": _observed(hparams.get("seed", {}))},
            "falsifiable_checkpoint": "The emitter output is compared with declared values and tolerances; no training claim is made.",
        },
    ]
    return {
        "plan_version": "1.0",
        "status": "PLANNED",
        "source_schema_version": setup.get("schema_version", "UNKNOWN"),
        "honesty": f"{HONESTY_BOUNDARY} A plan is not evidence that an experiment ran.",
        "steps": steps,
    }
