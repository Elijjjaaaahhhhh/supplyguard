# Phase 9 operational guide

SupplyGuard can now run ingestion, warehouse rebuilding, operational model fitting/reuse, next-day scoring, scenario checks, inventory decisions, constraints, prioritisation and shared-capital allocation with one command. Power BI consumes the resulting marts when refreshed manually. The approved PBIX is not edited or refreshed by this command.

## Setup and commands

Run from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m supplyguard.pipeline --dry-run
.\.venv\Scripts\python.exe -m supplyguard.pipeline
```

Use `config/pipeline.toml` for the budget (default 300,000), urgency weights, scenario size, seed, model threads, artifact location, and next-day holiday assumption. Database credentials remain in `.env` (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`). Run settings are recorded without credentials.

```powershell
# Explicit historical cutoff; must have 28 consecutive days for all scored series.
.\.venv\Scripts\python.exe -m supplyguard.pipeline --as-of 2024-07-02

# Refit even when matching model/data/version metadata already exists.
.\.venv\Scripts\python.exe -m supplyguard.pipeline --retrain

# Deliberately replace synthetic inputs for a different cutoff/size/seed.
.\.venv\Scripts\python.exe -m supplyguard.pipeline --as-of 2024-07-02 --regenerate-scenario

# Use a separate checked configuration for another budget or policy.
.\.venv\Scripts\python.exe -m supplyguard.pipeline --config config/pipeline.toml
```

The default preserves the existing 1,000-series scenario. A mismatching scenario date or size stops publication rather than silently changing it. `--regenerate-scenario` uses deterministic sampling but may select different series from the original development sampler. New scenario inputs are always labelled synthetic.

## Forecast meaning

The operational V3C model uses the same 27-feature design and core hyperparameters as the selected model, fitted through the chosen cutoff. It forecasts the **next day**, rather than treating historical holdout predictions as future forecasts. A July 2 cutoff produces July 3 forecasts.

Forward features use only observations through the cutoff. The 28-day window must be complete for every historical series. Next-day discount and activity are explicitly carried forward from the last observation; the holiday flag comes from configuration. These are assumptions, not known future retailer inputs. Supply real planned commercial inputs before using this as an operational business system.

The inventory engine uses that next-day forecast as a constant expected daily level across lead time and the planning horizon. It is **not** a separate multi-horizon forecast. The existing 0.01 demand floor remains explicit in SQL; stored forecasts themselves retain zero predictions. Demand variability still comes from training-period historical sales through the cutoff, not calibrated forecast errors. Observed sales remain censored by stockouts, and all operational inventory/supplier inputs remain synthetic.

The final historical evaluation script and its CSV are preserved. Operational refitting through July 2 must not be reported as a new untouched holdout evaluation.

## Persistence and reproducibility

- `ops.pipeline_run`: configuration, cutoff, Git revision/dirty indicator, model identifier, status, timing, summary and failure reason.
- `ops.pipeline_stage`: each stage's status, timings and details.
- `ops.source_file`: SHA-256 fingerprints and row counts. First adoption compares existing raw rows with their source files. Subsequent changed files are rejected pending an explicit migration.
- `ops.model_artifact`: training input fingerprint, feature order, hyperparameters, software versions, implementation fingerprint and artifact checksum.
- `ops.forecast`: immutable per-run store/SKU predictions, cutoff, target date, model identifier and input assumptions.
- `mart.inventory_decision` and `mart.control_tower`: forecast run/model/target lineage columns.
- `mart.bi_pipeline_status`: the most recent successful run for a future BI governance addition.
- `outputs/production/models/<model_id>/`: fitted model and manifest.
- `outputs/production/runs/<run_id>/`: pipeline log and successful summary.

Models are reused only when training inputs, cutoff, feature order, parameters, implementation and recorded software versions match. The stored model checksum is verified before loading. Only load locally trusted model artifacts; joblib files are executable Python serialization.

`requirements-lock.txt` records the validated environment. Python 3.14 is required by the package. Reproduce dependencies in an isolated environment using that file, then install this package with `--no-deps -e .`.

## Transaction boundaries and recovery

The pipeline holds a PostgreSQL advisory lock for its whole run. A second pipeline fails immediately rather than overlapping. Direct manual SQL sessions do not participate in that lock; do not edit marts during a pipeline run.

Ingestion commits each source through the existing ingestion function. Warehouse/feature rebuilding is one transaction. Model artifacts and forecasts are persisted before publication. Scenario replacement (if requested), all decision tables, quality gates and the successful run record share one publication transaction. If publication fails, the prior decision tables and scenario remain available. A failed run may retain useful model/forecast artifacts, but cannot become the published control tower.

After an interrupted process, rerun the command. Once it obtains the exclusive lock, it marks abandoned running records failed. Already registered unchanged sources are reused. No partial-stage resume is attempted; rerunning repeats the deterministic stages. A failed publication does not roll back successfully completed ingestion or warehouse stages.

The pipeline deliberately skips legacy `031_allocate_shared_capital.sql`: the report uses procurement-valid allocation from script 032. Historical scripts remain available for reference. Script 028 now requires the pipeline's forecast run/cutoff settings and is not a standalone historical-proxy loader.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q

# Requires one successful pipeline run. All test mutations roll back.
$env:SUPPLYGUARD_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:\SUPPLYGUARD_DB_TESTS
```

Checks cover forward feature cutoffs, incomplete histories, invalid configuration, budget validity, whole case packs, MOQ, forecast lineage, failed-publication rollback and zero-budget behaviour. These do not establish forecast service-level calibration or business benefit.

## Scheduling and Power BI

`scripts/run_pipeline.ps1` is a scheduler-friendly wrapper that returns the pipeline exit code. To schedule later, use Windows Task Scheduler with the wrapper's absolute path and an account that can access the project, its environment and PostgreSQL. Choose the desired frequency explicitly; no recurring job is installed by Phase 9.

Refreshing Power BI is a separate step. The saved Phase 8 PBIX continues to show its approved imported snapshot until a user refreshes it. New operational forecasts can change recommendation counts and allocated totals. The preserved historical prediction CSV and any report-specific imported forecast tables are not automatically replaced by the operational forecast table. Adding live run governance/operational forecast visuals is a separate report change.

## Remaining scope

This is a local batch productionisation foundation: no hosted deployment, automatic Power BI service refresh, drift alerts, live retailer integrations, probabilistic forecasts, or automated purchasing. Phase 10 can package and demonstrate this reproducible workflow.


## Rebuild correction found during validation

The original dimension loader attempted to insert all distinct store/city/group tuples into a dimension keyed only by store. The source contains concurrent multiple management groups per store. Rebuilds now preserve these associations in `core.bridge_store_management_group` and use an explicitly labelled mixed-group sentinel in the compatibility column. The store key and existing BI view columns remain. The BI store view exposes the mixed-group sentinel through `management_group_id`; a descriptive group-label column is not currently created.


## Acceptance results

The complete pipeline succeeded on the local 4.85-million-row dataset. It trained the operational model on 3.45 million rows, saved 50,000 next-day forecasts, and published 1,000 decision rows with complete forecast lineage. All 22 tests passed, including rollback-only PostgreSQL checks, exact historical SQL/forward-feature agreement, budget/MOQ cases, deterministic republication, and saved-model reuse with refitting disabled. The approved PBIX checksum remained unchanged. No schedule, commit or push was performed.
