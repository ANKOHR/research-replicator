"""Deterministic fictional paper and CPU metric-emitter fixtures."""

from __future__ import annotations

import hashlib
from pathlib import Path

from .io import write_json, write_text


PAPER = """# ToyDigits: A Fictional Synthetic Benchmark

This document and every number in it are synthetic and fictional. It describes no real paper, dataset, model, or benchmark.

## Experimental Setup

### Datasets
- name: ToyDigits-v1

### Model
- architecture: LinearToyClassifier

### Hyperparameters
- learning_rate: 0.1
- batch_size: 16
- epochs: 3
- seed: 7
- optimizer: toy_sgd

### Metrics
| metric | unit | tolerance |
| --- | --- | --- |
| accuracy | fraction | 0.02 |
| loss | toy-loss-units | 0.05 |

### Reported Results
| metric | value | unit | tolerance |
| --- | ---: | --- | ---: |
| accuracy | 0.77 | fraction | 0.02 |
| loss | 0.24 | toy-loss-units | 0.05 |
"""

NO_EXPERIMENTS = """# Synthetic Note About Labelled Shapes

This fictional synthetic note is provided only to test empty extraction behavior.

## Abstract
It discusses imaginary shapes without an experiment, dataset, model, metric, or result.

## Closing Note
No experimental setup is included in this fixture.
"""

MISSING_HYPERPARAMETERS = """# A Fictional Paper With Missing Settings

This document is synthetic and fictional. The declared setup intentionally omits all hyperparameters.

## Experimental Setup

### Datasets
- name: PaperShapes-v0

### Model
- architecture: UnspecifiedToyModel

### Hyperparameters
Not disclosed in this fictional paper.

### Metrics
| metric | unit | tolerance |
| --- | --- | ---: |
| score | points | 1.0 |

### Reported Results
| metric | value | unit | tolerance |
| --- | ---: | --- | ---: |
| score | 10 | points | 1.0 |
"""

TRAIN_SCRIPT = '''"""Emit deterministic synthetic metrics. This script does no model training."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    epochs = int(config["epochs"])
    rate = float(config["learning_rate"])
    accuracy = round(min(0.99, 0.70 + 0.02 * epochs + 0.05 * rate), 6)
    loss = round(max(0.0, 1.0 / (1 + epochs) - 0.1 * rate), 6)
    print(json.dumps({"metrics": [
        {"name": "accuracy", "value": accuracy, "unit": "fraction"},
        {"name": "loss", "value": loss, "unit": "toy-loss-units"},
    ]}, sort_keys=True))


if __name__ == "__main__":
    main()
'''


def create_fixtures(output: str | Path) -> list[str]:
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    repo = root / "synthetic-repo"
    repo.mkdir(parents=True, exist_ok=True)
    paths = {
        "paper": root / "toy-paper.md",
        "empty_paper": root / "no-experiments-paper.md",
        "missing_hyperparameters_paper": root / "missing-hyperparameters-paper.md",
        "repo_manifest": repo / "repkit-fixture.json",
        "repo_script": repo / "train.py",
        "repo_config": repo / "config.json",
    }
    write_text(paths["paper"], PAPER)
    write_text(paths["empty_paper"], NO_EXPERIMENTS)
    write_text(paths["missing_hyperparameters_paper"], MISSING_HYPERPARAMETERS)
    write_text(paths["repo_script"], TRAIN_SCRIPT)
    write_json(paths["repo_manifest"], {
        "fixture": True,
        "kind": "synthetic_metric_emitter",
        "description": "Fictional deterministic CPU metric emitter; performs no model training.",
        "script_sha256": hashlib.sha256(paths["repo_script"].read_bytes()).hexdigest(),
    })
    write_json(paths["repo_config"], {
        "learning_rate": 0.1,
        "batch_size": 16,
        "epochs": 3,
        "seed": 7,
        "optimizer": "toy_sgd",
    })
    return [str(path) for path in paths.values()]
