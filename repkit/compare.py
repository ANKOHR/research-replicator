"""Tolerance-based comparison of declared targets and observed fixture metrics."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .io import RepkitError
from .schema import HONESTY_BOUNDARY, UNKNOWN


def _number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def compare_records(paper_results: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    reported = paper_results.get("reported_results", [])
    metrics = observed.get("metrics", [])
    if not isinstance(reported, list) or not isinstance(metrics, list):
        raise RepkitError("Paper results and observed metrics must be lists.")
    observed_by_name: dict[str, dict[str, Any]] = {}
    for item in metrics:
        if isinstance(item, dict) and "name" in item:
            observed_by_name[str(item["name"])] = item
    rows = []
    for target in reported:
        if not isinstance(target, dict) or "metric" not in target:
            continue
        name = str(target["metric"])
        actual = observed_by_name.get(name)
        tolerance_value = target.get("tolerance", UNKNOWN.copy())
        if isinstance(tolerance_value, dict) and tolerance_value.get("status") == "UNKNOWN":
            tolerance_display = "UNKNOWN"
        else:
            tolerance_display = tolerance_value
        row: dict[str, Any] = {
            "metric": name,
            "reported": target.get("value", "UNKNOWN"),
            "observed": actual.get("value", "MISSING") if actual else "MISSING",
            "unit": target.get("unit", "UNKNOWN"),
            "reported_source_section": target.get("source_section"),
            "tolerance": tolerance_display,
            "tolerance_source_section": target.get("tolerance_source_section"),
        }
        if actual is None:
            row["status"] = "MISSING_OBSERVATION"
        elif str(target.get("unit", "UNKNOWN")) == "UNKNOWN" or str(actual.get("unit", "UNKNOWN")) == "UNKNOWN":
            row["status"] = "UNIT_UNKNOWN"
            row["observed_unit"] = actual.get("unit", "UNKNOWN")
        elif str(actual.get("unit")) != str(target.get("unit", "UNKNOWN")):
            row["status"] = "UNIT_MISMATCH"
            row["observed_unit"] = actual.get("unit", "UNKNOWN")
        else:
            expected_number = _number(target.get("value"))
            actual_number = _number(actual.get("value"))
            tolerance_number = _number(tolerance_value)
            if expected_number is None or actual_number is None:
                row["status"] = "NON_NUMERIC_VALUE"
            elif tolerance_number is None:
                row["status"] = "TOLERANCE_UNKNOWN"
            elif tolerance_number < 0:
                raise RepkitError(f"Tolerance for {name} cannot be negative.")
            else:
                difference = abs(actual_number - expected_number)
                row["difference"] = float(difference)
                row["status"] = "PASS" if difference <= tolerance_number else "OUT_OF_TOLERANCE"
        rows.append(row)
    rows.sort(key=lambda row: row["metric"])
    statuses = [row["status"] for row in rows]
    if not rows:
        overall = "NO_REPORTED_METRICS"
    elif all(status == "PASS" for status in statuses):
        overall = "PASS"
    elif any(status in {"OUT_OF_TOLERANCE", "UNIT_MISMATCH", "MISSING_OBSERVATION"} for status in statuses):
        overall = "FAIL"
    else:
        overall = "INCOMPLETE"
    return {
        "comparison_version": "1.0",
        "config_id": observed.get("config_id"),
        "run_id": observed.get("run_id"),
        "overall_status": overall,
        "honesty": f"{HONESTY_BOUNDARY} The comparison does not reproduce a paper.",
        "metrics": rows,
    }
