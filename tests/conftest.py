from __future__ import annotations

import json
from pathlib import Path

import pytest

from repkit.fixtures import create_fixtures


@pytest.fixture
def fixture_files(tmp_path: Path) -> dict[str, Path]:
    paths = [Path(item) for item in create_fixtures(tmp_path / "fixtures")]
    return {
        "paper": paths[0],
        "empty_paper": paths[1],
        "missing_hparams": paths[2],
        "manifest": paths[3],
        "script": paths[4],
        "config": paths[5],
        "repo": paths[3].parent,
    }


@pytest.fixture
def read_json_file():
    def read(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    return read
