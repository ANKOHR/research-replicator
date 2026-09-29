# ResearchReplicator

ResearchReplicator extracts declared experimental details from fictional Markdown fixtures, creates a sourced reproduction plan, tracks config changes, invokes a deterministic CPU metric emitter, and compares emitted values with declared targets and tolerances. It is a synthetic workflow demonstration for research engineering practices.

## Quickstart

Use Python 3.10 or newer. The runtime has no ML framework dependencies.

```powershell
python -m pip install -e .[test]
repkit fixtures --out .\demo
repkit extract .\demo\toy-paper.md --out .\demo\setup.json --state-dir .\demo\workflow
repkit plan .\demo\setup.json --out .\demo\plan.json --state-dir .\demo\workflow
repkit track --config .\demo\synthetic-repo\config.json --reason "fixture baseline" --state-dir .\demo\workflow
```

Copy the `config_id` printed by `track` into the run command:

```powershell
repkit run --config cfg-REPLACE_WITH_PRINTED_ID --repo .\demo\synthetic-repo --state-dir .\demo\workflow
repkit compare .\demo\setup.json .\demo\workflow\observed.json --state-dir .\demo\workflow
repkit report --format md --state-dir .\demo\workflow
repkit report --format html --state-dir .\demo\workflow
```

The comparison and reports are written in the workflow directory. `python -m pytest` runs the full test suite.

## HONESTY BOUNDARY

ResearchReplicator analyzes documents and plans reproductions; it NEVER runs GPU training and NEVER claims to have reproduced published results. The CLI output, reports, and README state this plainly: synthetic papers and repos only, extraction and planning over declared fixtures, no training runs, no real papers, no real models. The checked-in and generated papers and repos are synthetic, fictional, and labelled as such. The fixture script computes deterministic stand-in numbers from a JSON config. It does no model training and accesses no GPU. `repkit run` accepts only a repo declared as a synthetic fixture and verifies the metric-emitter script hash before invoking it. These outputs are not results from a real model, paper, dataset, or benchmark.

## Architecture

```text
fictional Markdown paper
        |
        v
  extract -> typed setup record with source sections and UNKNOWN fields
        |
        v
    plan -> ordered steps, expected observations, controls, checkpoints
        |
        +------------------------------+
        |                              |
        v                              v
  track configs                  synthetic fixture repo
  snapshots + diffs                     |
        |                                v
        +--------------------------> run -> observed stand-in metrics
                                           |
setup reported results -------------------+
                                           v
                                  compare -> tolerances
                                           |
                                           v
                                     report -> md or html
```

Persistent workflow artifacts live under `.repkit` by default. Pass `--state-dir` to use a different directory. The default state directory is ignored by Git.

## Fixture catalogue

`repkit fixtures --out DIR` writes:

- `toy-paper.md`: synthetic setup with datasets, architecture, hyperparameters, metrics, tolerances, and reported values.
- `no-experiments-paper.md`: a fictional paper with no experiments section, for testing typed empty extraction.
- `missing-hyperparameters-paper.md`: a fictional setup with the hyperparameters intentionally undisclosed.
- `synthetic-repo/`: a deterministic CPU script, config, and manifest. The script emits metrics and performs no training.

All fixture names, papers, datasets, models, values, and results are invented for this project.

## Setup schema reference

An extraction is JSON with `schema_version`, `paper`, `sections`, `datasets`, `model`, `hyperparameters`, `metrics`, and `reported_results`.

| Field | Shape | Meaning |
| --- | --- | --- |
| `paper.title` | sourced value | Title and its source section. |
| `sections.experiments` | `{status, source_section}` | `PRESENT` only when a recognized experiment section exists. Otherwise `UNKNOWN`. |
| `datasets` | list of `{name, source_section}` | Dataset names declared under the setup's Datasets heading. |
| `model.architecture` | sourced value or UNKNOWN | Declared architecture. |
| `hyperparameters` | map of sourced values or UNKNOWN | `learning_rate`, `batch_size`, `epochs`, `seed`, and `optimizer`. |
| `metrics` | list of `{name, unit, tolerance?, source_section}` | Declared metric names and units. A tolerance is included only when declared. |
| `reported_results` | list of `{metric, value, unit, tolerance?, source_section}` | Reported target values with units and tolerance provenance. |

A sourced value is `{ "value": VALUE, "source_section": "Heading" }`. An absent scalar is `{ "status": "UNKNOWN", "source_section": null }`. Empty sections stay empty. No defaults are guessed. Tolerance values may come from the corresponding Metrics table; `tolerance_source_section` identifies where that tolerance was declared.

The parser recognizes a Markdown heading named `Experimental Setup`, `Experiments`, or `Experimental Details`. Under it, use headings containing `Datasets`, `Model`, `Hyperparameters`, `Metrics`, or `Results`. Key/value bullets such as `- learning_rate: 0.1` and Markdown tables with headers are supported. Results tables use `metric`, `value`, and optionally `unit` and `tolerance` columns.

## Plan format

`repkit plan SETUP.json` writes a JSON plan with `plan_version`, `status`, `source_schema_version`, an honesty statement, and an ordered `steps` array. Every step has:

- `order` and stable `id` fields.
- `action`, stated using extracted setup information.
- `field_refs`, JSON Pointers into the setup record.
- `expected_observations`, copied from extracted values or marked `UNKNOWN`.
- `controls`, including the declared seed when present.
- `falsifiable_checkpoint`, a check that can fail if fields are absent or inconsistent.

The final step describes synthetic metric emission for a fixture repo. It states that no model training occurs. A plan is not evidence that an experiment ran.

## Config tracking and comparison

`repkit track --config CONFIG.json` stores a content-addressed config snapshot and a recursive JSON diff from the previously tracked config. Each history event includes a UTC timestamp, reason, parent config ID, and changed paths. Config IDs identify the JSON contents, so running the same config refers to the same snapshot.

`repkit run --config ID --repo DIR` requires the manifest emitted by `repkit fixtures`, verifies the script hash, sets CPU-only environment flags, and invokes only `train.py`. The script produces deterministic synthetic observations. It does not train a model.

`repkit compare PAPER_RESULTS OBSERVED` computes the absolute difference for each numeric metric and passes when `difference <= declared tolerance`. It also checks units. Missing observations, mismatched units, or out-of-tolerance values fail; unknown tolerances remain incomplete instead of passing. Comparisons contain no timestamps so rerunning the same inputs yields byte-identical JSON.

## Reports and provenance

`repkit report --format md|html` assembles the setup record, plan, config event history, comparison table, and provenance counts from the selected workflow directory. The HTML report includes a visible honesty banner. Reports identify synthetic metric emission and do not claim reproduction.

## CLI commands

- `fixtures --out DIR`: write the deterministic fictional fixtures.
- `extract PAPER.md`: extract sourced setup values.
- `plan SETUP.json`: build a reproduction plan.
- `track --config CONFIG.json`: record a config version and diff.
- `run --config ID --repo DIR`: emit synthetic CPU observations from a declared fixture only.
- `compare PAPER_RESULTS OBSERVED`: compare numbers and declared tolerances.
- `report --format md|html`: assemble workflow artifacts with provenance.

Use `repkit COMMAND --help` for command options. The top-level and run help repeat the honesty boundary.
