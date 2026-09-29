from __future__ import annotations

from repkit.extract import extract_file


def test_extracts_every_planted_field_with_source_citations(fixture_files):
    setup = extract_file(fixture_files["paper"])
    assert setup["paper"]["title"]["value"] == "ToyDigits: A Fictional Synthetic Benchmark"
    assert setup["paper"]["title"]["source_section"] == "Document title"
    assert setup["sections"]["experiments"]["status"] == "PRESENT"
    assert setup["datasets"] == [{"name": "ToyDigits-v1", "source_section": "Datasets"}]
    assert setup["model"]["architecture"] == {"value": "LinearToyClassifier", "source_section": "Model"}
    assert {key: value["value"] for key, value in setup["hyperparameters"].items()} == {
        "learning_rate": 0.1, "batch_size": 16, "epochs": 3, "seed": 7, "optimizer": "toy_sgd"
    }
    assert all(value["source_section"] == "Hyperparameters" for value in setup["hyperparameters"].values())
    assert [(row["name"], row["unit"], row["tolerance"]) for row in setup["metrics"]] == [
        ("accuracy", "fraction", 0.02), ("loss", "toy-loss-units", 0.05)
    ]
    assert all(row["source_section"] == "Metrics" for row in setup["metrics"])
    assert [(row["metric"], row["value"], row["unit"]) for row in setup["reported_results"]] == [
        ("accuracy", 0.77, "fraction"), ("loss", 0.24, "toy-loss-units")
    ]
    assert all(row["source_section"] == "Reported Results" for row in setup["reported_results"])


def test_experiments_free_paper_is_typed_empty_and_invents_nothing(fixture_files):
    setup = extract_file(fixture_files["empty_paper"])
    assert setup["sections"]["experiments"]["status"] == "UNKNOWN"
    assert setup["sections"]["experiments"]["source_section"] is None
    assert setup["datasets"] == []
    assert setup["metrics"] == []
    assert setup["reported_results"] == []
    assert setup["model"]["architecture"] == {"status": "UNKNOWN", "source_section": None}
    assert all(value == {"status": "UNKNOWN", "source_section": None} for value in setup["hyperparameters"].values())


def test_missing_hyperparameters_are_unknown_not_filled(fixture_files):
    setup = extract_file(fixture_files["missing_hparams"])
    assert setup["sections"]["experiments"]["status"] == "PRESENT"
    assert all(value["status"] == "UNKNOWN" for value in setup["hyperparameters"].values())
    assert setup["reported_results"][0]["metric"] == "score"
