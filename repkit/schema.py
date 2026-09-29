"""Typed setup records and stable JSON helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


UNKNOWN: dict[str, Any] = {"status": "UNKNOWN", "source_section": None}
HYPERPARAMETER_FIELDS = (
    "learning_rate",
    "batch_size",
    "epochs",
    "seed",
    "optimizer",
)


@dataclass(frozen=True)
class SourcedValue:
    value: Any
    source_section: str

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.value, "source_section": self.source_section}


@dataclass(frozen=True)
class SetupRecord:
    schema_version: str
    title: SourcedValue | dict[str, Any]
    experiments_status: str
    experiments_source_section: str | None = None
    datasets: list[dict[str, Any]] = field(default_factory=list)
    architecture: SourcedValue | dict[str, Any] = field(default_factory=lambda: UNKNOWN.copy())
    hyperparameters: dict[str, SourcedValue | dict[str, Any]] = field(default_factory=dict)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    reported_results: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        title = self.title.as_dict() if isinstance(self.title, SourcedValue) else self.title
        architecture = self.architecture.as_dict() if isinstance(self.architecture, SourcedValue) else self.architecture
        hparams = {
            key: value.as_dict() if isinstance(value, SourcedValue) else value
            for key, value in self.hyperparameters.items()
        }
        return {
            "schema_version": self.schema_version,
            "paper": {"title": title},
            "sections": {
                "experiments": {
                    "status": self.experiments_status,
                    "source_section": self.experiments_source_section,
                }
            },
            "datasets": self.datasets,
            "model": {"architecture": architecture},
            "hyperparameters": hparams,
            "metrics": self.metrics,
            "reported_results": self.reported_results,
        }
