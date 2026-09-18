# SupplyGuard — interview and portfolio guide

## 30-second pitch

SupplyGuard connects demand forecasting to inventory decisions. I built a PostgreSQL warehouse and a leakage-safe next-day forecasting model, then used its predictions in a scenario inventory engine that applies supplier rules, capacity, shelf life and a shared capital budget. Power BI makes the full path visible—from observed sales and historical model accuracy to risk, feasible replenishment, funding and action. Operational inputs are simulated, and I make that boundary explicit.

## Two-to-three-minute walkthrough

Start with the business problem: an accurate forecast still does not tell a planner what to purchase. Introduce the 4.85-million-row observed-sales dataset and the warehouse layers. Explain why stockouts mean observed sales are not unconstrained demand.

Show the historical model-governance page. Use chronological training, validation and untouched holdout periods to explain leakage prevention. The frozen V3C model achieved MAE 0.3815, RMSE 0.6933 and WAPE 31.98%, compared with 0.4129, 0.6948 and 34.61% for the seven-day rolling baseline. Typical absolute error improved; the reduction in large errors was much smaller.

Open Forecast & Inventory Outlook and choose a scenario store/product. Read the historical sales and historical actual-versus-predicted charts. Point to the explicit next-day target date. Explain that the forecast is next-day only, while inventory planning extrapolates that level.

Trace scenario on-hand, on-order and backorders into inventory position, coverage and reorder point. Follow raw need into a feasible recommendation and then funded quantity. Explain one binding constraint and the recommended action. Finish with run/model lineage and the repeatable local batch command. Avoid claiming real retailer savings or deployed automation.

## Technical defence

| Topic | Defensible explanation |
|---|---|
| Business problem | Planners must allocate scarce procurement capital across competing stock risks; prediction is one input. |
| PostgreSQL | Relational grain checks, inspectable SQL, transactions and BI connectivity make decision lineage easy to audit. |
| Layer separation | Raw preserves evidence; staging cleans types; core standardises entities; features enforce temporal logic; marts expose stable decisions. |
| Temporal validation | Future observations must not influence training or model selection. Holdout is reserved until the feature design is frozen. |
| Leakage prevention | Rolling windows exclude the target row; forward scoring uses a complete history ending at the cutoff. Future commercial values are explicit carry-forward assumptions. |
| Metrics | MAE measures typical absolute error; RMSE emphasises large misses; WAPE scales error by total actual sales and is undefined for zero-total selections. |
| HistGradientBoosting | Captures nonlinear interactions in tabular history/commercial features; relatively practical batch training. It was compared with simple baselines. |
| V1 → V2 → V3 | V1 establishes ML, V2 enriches temporal history, V3 evaluates external/commercial information. V3C retains history and commercial features. |
| Ablation / weather | Validation showed commercial inputs helped and weather did not improve the selected design. That is dataset/window evidence, not a universal conclusion about weather. |
| Forecast limitations | Short history, stockout-censored targets, assumed future commercial inputs, point predictions and next-day horizon. |
| Safety stock / service level | A policy approximation combining demand and lead-time variability. Synthetic service targets have not been calibrated against real service outcomes. |
| Reorder point | Expected demand over lead time plus safety stock; trigger differs from planning-horizon target. |
| Days of supply | Inventory coverage divided by expected daily consumption; interpret alongside lead time and the explicit demand floor. |
| MOQ / case packs | A funded quantity must satisfy both procurement constraints; affordable fractions of a pack are not valid purchases. |
| Capital / capacity / shelf life | Per-item caps restrict feasibility before the shared budget allocates funding. Constraints are exposed rather than hiding unmet need. |
| Urgency | Weighted coverage gap, stockout cost, demand, unmet need, supplier risk and business priority; policy weights are assumptions. |
| Greedy funding | Transparent, reproducible prioritisation with valid packs/MOQ. It is not a proof of global optimality; optimisation needs credible objectives and costs first. |
| Observed vs scenario | Sales and source availability are observed; forecasts are predicted; operational inventory/supplier/economic inputs are simulated. |
| ERP / WMS integration | Replace scenario generators with timestamped inventory snapshots, purchase orders, receipts, supplier masters, costs and capacity feeds; reconcile keys and units first. |
| Production changes | Validate business policies, future-feature availability, service calibration, governance, recovery and access controls; then add scheduling, monitoring and deployment as separate work. |

## CV-ready bullets

- Built an end-to-end Python/PostgreSQL supply-chain decision-support project over 4.85 million retail observations, with temporal features and auditable forecast/run lineage.
- Evaluated a frozen HistGradientBoosting model on 350,000 held-out observations; reduced MAE by approximately 7.6% versus a seven-day rolling baseline (0.3815 vs 0.4129).
- Implemented a 1,000-series synthetic inventory scenario with safety stock, reorder points, operational constraints and procurement-valid allocation of a 300,000-unit shared budget.
- Developed a Power BI control tower connecting observed sales, next-day forecasts, scenario inventory risk, replenishment feasibility and recommended actions.

## Portfolio description

SupplyGuard is a reproducible local supply-chain control tower linking a retail analytical warehouse, next-day forecasting and transparent inventory decisions. Its value is the auditable connection between prediction and action, with explicit distinctions between observed source data, model predictions and synthetic operating scenarios. It demonstrates engineering and analytical reasoning, not claimed retailer business impact.

## Limitations and future roadmap

Current limits include short history, censored sales, synthetic operating policies, assumed next-day commercial inputs, uncalibrated service levels and a greedy allocator. Future work can evaluate true multi-horizon and probabilistic forecasting, lost-sales treatment, real ERP/WMS feeds, optimisation, scheduling, cloud deployment and drift monitoring. These are separately scoped enhancements, not blockers to the local batch project.
