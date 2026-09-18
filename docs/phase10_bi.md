# Phase 10 — BI and demonstration guide

## Stable interfaces

- `mart.bi_demand_history`: observed daily sales/availability for the published 1,000-series scenario; `(store_id, product_id, dt)` grain.
- `mart.bi_forecast_evaluation`: all 350,000 saved historical holdout observations, actuals, V3C and rolling predictions. `ops.forecast_evaluation` stores the source SHA-256 and frozen model label. Changed source files require an explicit reviewed migration.
- `mart.bi_forecast_outlook`: one row per published scenario series, joining the exact forecast run, model and target date used by `mart.control_tower`. Includes synthetic operating inputs, risk, constraints, procurement rules, funded quantities and action.

The views are published and validated in the existing decision-publication transaction. Historical evaluation is loaded only once, verified against observed sales, and never overwritten by operational refitting. Existing Power BI history/evaluation tables retain their names and relationships while their sources change to these interfaces.

## Reproduction

Use the existing setup in README and `docs/phase9_operations.md`. Preserve the final historical evaluation CSV at `outputs/final_v3c_predictions.csv`; generate it with `python -m supplyguard.models.final_evaluation` only when reproducing the historical experiment in a matching environment. The first Phase 10 publication validates and imports it. Subsequent changed fingerprints fail rather than silently replacing historical evidence.

```powershell
.\.venv\Scripts\python.exe -m supplyguard.pipeline
$env:SUPPLYGUARD_DB_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:\SUPPLYGUARD_DB_TESTS
.\.venv\Scripts\python.exe -m supplyguard.validation
.\.venv\Scripts\python.exe scripts/reconcile_phase10.py
```

Open the approved report and refresh after the pipeline succeeds. A successful pipeline does not itself refresh Power BI. Read the explicitly dated forecast and compare the saved report totals to the latest published run. The expected demonstration cutoff is 2 July 2024 and forecast date is 3 July 2024; these are dataset dates, not current live operations.

## New page

Forecast & Inventory Outlook follows observed sales → historical actual/predicted performance → dated next-day forecast → synthetic inventory → inventory risk → raw/feasible/funded quantities → status/action. Store and Product slicers use the existing dimensions and scenario-availability filtering. Operational detail cards require exactly one scenario series; no selection asks the viewer to choose a pair. Historical evaluation metrics follow the selection; the governance page retains all-series metrics when unfiltered. WAPE returns blank when total actual sales are zero.

Chart clicks on this page do not silently change the operational recommendation. Slicers filter all relevant visuals. Forecast date is independent of the historical date dimension, which ends before the target date. Days of supply, lead time, safety stock and reorder point are intentionally not added across multiple products.

## Interpretation

The next-day forecast is the stored raw prediction. The inventory engine applies an explicit 0.01 minimum demand level for its calculations. Synthetic currency has no USD/NGN designation. No simulated result is presented as measured savings or retailer expenditure. Existing approved pages are retained, with necessary factual label/format corrections.

See `architecture.md` for flow and mathematical assumptions and `interview_readiness.md` for the pitch, walkthrough and technical defence. See the reconciliation evidence for tested examples and actual execution results.

The reconciliation script checks six representative cases against source history, baseline mathematics, saved-model predictions, scenario inputs and decision calculations. It writes local detailed evidence under `outputs/production/phase10/`. Reviewable DAX and import-partition extracts are in `docs/powerbi-model/`.
