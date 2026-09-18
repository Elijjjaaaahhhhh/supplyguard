# Phase 10 audit and acceptance notes

## Existing and reused

Clean `main` at `6c512b1`; approved `app/SupplyGuard.pbix` with seven pages and 180 visuals; completed local pipeline; versioned V3C operational model; 50,000 persisted next-day forecasts per run; 1,000 scenario decisions; existing historical prediction CSV and Power BI measures/relationships.

## Gaps and changes

Historical evaluation depended on a local CSV in Power BI; observed history used implementation-level SQL; operational forecasts were not exposed through a stable BI interface or dated report card. Added `ops.forecast_evaluation` and `mart.bi_demand_history`, `mart.bi_forecast_evaluation`, `mart.bi_forecast_outlook`. Source SHA-256, unique grain, actuals reconciliation, target dates and published forecast lineage are validated. Publication reuses existing pipeline transactions.

The new Outlook table links to existing Store and Product dimensions. The eight-page report retains all 180 approved visuals, adds 36 outlook visuals and seven navigation buttons, and corrects stale rolling-proxy, currency and QA-snapshot wording. No forecast model, allocation algorithm or scenario inputs were replaced.

## Confirmed historical evaluation

350,000 rows, 26 June–2 July 2024, with no duplicate series/date keys. V3C: MAE 0.3815378897, RMSE 0.6932557971, WAPE 0.3197996353. Rolling baseline: MAE 0.4129037282, RMSE 0.6947525029, WAPE 0.3460900353. Source SHA-256: `60fbd09d1a7b2727bde6cb31bf37fd96cc3393ecae6911a21686319b94b7667f`.

## Representative cases

| Case | Store | Product | Status |
|---|---:|---:|---|
| Healthy | 1 | 38 | HEALTHY |
| Watch | 9 | 115 | WATCH |
| Critical urgency | 21 | 267 | CONSTRAINED - ESCALATE |
| Constrained | 0 | 21 | CONSTRAINED - ESCALATE |
| Funded | 1 | 300 | REORDER - FUNDED |
| Unfunded | 1 | 117 | REORDER - UNFUNDED |

There are two CRITICAL-urgency cases; both are constrained. No current status starts with CRITICAL. Healthy/watch rows have no urgency rank and the outlook displays “Not ranked”.

The first six-case comparison passed all 192 comparable database/Power BI fields (publication timestamp excluded from the locale-formatted comparison). Independently re-scored model predictions match; 97 historical observations and seven evaluation observations per series were reconciled, including recomputed rolling baselines. Direct scenario inputs, coverage, safety stock, reorder point, raw requirement, feasible quantities and procurement-valid funding all passed.

## Execution gates

- Ten existing unit tests passed before final integration QA.
- Warehouse rebuild passed: 4,850,000 rows and 897 stores with explicitly mixed management groups.
- All existing warehouse validations passed: counts, unique business keys, nonnegative sales, stockout range and dimension integrity.
- Complete pipeline and final report refresh succeeded. All 25 tests passed, including PostgreSQL rollback tests and saved-model reuse (1,150.57 seconds including time waiting for the pipeline lock).

## Boundaries

Only next-day ML forecasting is implemented. Planning demand is constant-level extrapolation. The inventory engine applies a 0.01 daily-demand floor while stored predictions retain zero. All operational inventory/supplier/economic inputs and the 300,000-unit budget are synthetic. No measured retailer benefit, multi-horizon accuracy or calibrated service-level performance is claimed. Scheduling, cloud deployment, drift infrastructure and advanced optimisation remain future work.

## Successful full batch run

Run `93fb3e65-00ba-4034-9716-bc42dda77790` completed all stages on 18 September 2026. It reused model `b9789f1a3402d4b0c0721679`, saved 50,000 forecasts for 3 July 2024 and published 1,000 decisions with matching forecast lineage. It reused scenario inputs and allocated 299,990.13 of 300,000 units. Total funded quantity: 11,140; funded orders: 84. The independent six-case reconciliation was repeated against this run and passed.

## Final refresh verification

Power BI full-model refresh succeeded. Table view shows 1,000 Outlook rows, forecast date 3 July 2024 and the complete new run ID `93fb3e65-00ba-4034-9716-bc42dda77790`; a screenshot records this evidence. The refreshed capital page shows budget 300,000.00, allocation 299,990.13 and remainder 9.87 in scenario units.

The connector declined the final post-refresh DAX query. It was not retried. The earlier 192-field comparison passed; final lineage, row count and headline totals were checked through the report UI instead. Full underlying six-case reconciliation was repeated against the new run and passed.

## Evidence and visual review

Detailed six-case source/model evidence is in `phase10_reconciliation.json`. Three screenshots in `assets/` document observed/predicted history, the inventory-to-action sequence and refreshed run lineage. All seven original pages and 180 original visuals are preserved; the report now has eight pages and 223 visuals. All real-currency labels were removed from report visuals and currency-formatted model fields.
