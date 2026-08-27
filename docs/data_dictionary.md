# SupplyGuard Data Dictionary

## Source

Primary downstream demand source: FreshRetailNet-50K.

SupplyGuard uses the dataset as real retail demand and stock-availability history. Upstream supplier, purchase-order, procurement and distribution-centre data will be added later as a clearly documented synthetic operational layer.

## Table Grain

One row represents one product at one store on one calendar date.

Expected business key:

`store_id + product_id + dt`

The training dataset contains 50,000 unique store-product series observed over 90 consecutive days.

---

## Columns

### city_id

**Type:** integer

**Meaning:** Identifier for the city associated with the store.

**Validation / constraints:**
- No missing values found.
- 18 unique values in the evaluation data.
- Treat as an identifier, not a numeric measurement.

**SupplyGuard usage:**
- Geographic segmentation.
- Store/network analysis.
- Potential regional demand or weather analysis.

---

### store_id

**Type:** integer

**Meaning:** Unique identifier for a retail store/location.

**Validation / constraints:**
- No missing values found.
- 898 unique stores observed.
- Part of the expected business key.

**SupplyGuard usage:**
- Store-level demand analysis.
- Store-product forecasting.
- Location-level inventory risk.
- Potential mapping to future distribution-centre or warehouse structures.

---

### management_group_id

**Type:** integer

**Meaning:** Identifier for the management grouping associated with a store or operational unit.

**Validation / constraints:**
- No missing values found.
- Exact business interpretation should remain tied to the source documentation.

**SupplyGuard usage:**
- Potential organisational segmentation.
- May support higher-level operational roll-ups if useful.

---

### first_category_id

**Type:** integer

**Meaning:** Highest-level product category identifier.

**Validation / constraints:**
- No missing values found.
- 32 unique values observed in evaluation data.
- Product-category mapping was consistent across the training data.

**SupplyGuard usage:**
- Category-level demand analysis.
- Product segmentation.
- Model and dashboard aggregation.

---

### second_category_id

**Type:** integer

**Meaning:** Second-level product category identifier.

**Validation / constraints:**
- No missing values found.
- 84 unique values observed in evaluation data.
- Product-category mapping was consistent across training data.

**SupplyGuard usage:**
- More detailed product segmentation.
- Category-specific demand behaviour.

---

### third_category_id

**Type:** integer

**Meaning:** Lowest available product-category identifier in the source hierarchy.

**Validation / constraints:**
- No missing values found.
- 233 unique values observed in evaluation data.
- Product-category mapping was consistent across training data.

**SupplyGuard usage:**
- Fine-grained product-family analysis.
- Potential forecasting or anomaly features.

---

### product_id

**Type:** integer

**Meaning:** Product/SKU identifier.

**Validation / constraints:**
- No missing values found.
- 865 unique products observed.
- Part of the expected business key.
- Each product mapped consistently to one category hierarchy in training data.

**SupplyGuard usage:**
- Core SKU-level analytical entity.
- Demand forecasting.
- Stockout analysis.
- Future replenishment and inventory recommendations.

---

### dt

**Type:** string in source; converted to datetime during processing

**Meaning:** Calendar date of the store-product observation.

**Validation / constraints:**
- No missing or invalid dates found.
- Training range: 2024-03-28 to 2024-06-25.
- Evaluation range: 2024-06-26 to 2024-07-02.
- Training contains 90 consecutive dates.
- Evaluation contains 7 consecutive dates.

**SupplyGuard usage:**
- Time-series ordering.
- Temporal features.
- Forecasting splits.
- Trend and seasonality analysis.

---

### sale_amount

**Type:** float

**Meaning:** Observed daily sales quantity for the store-product-date.

**Validation / constraints:**
- No missing values found.
- No negative values found.
- Training zero-sales rate: approximately 4.46%.
- Daily value matched the sum of `hours_sale` in the evaluation data.
- Important limitation: observed sales may underestimate true demand when the product is out of stock.

**SupplyGuard usage:**
- Primary observed demand measure.
- Forecasting target candidate.
- Demand analysis.
- Requires stockout-aware treatment because of censored demand.

---

### hours_sale

**Type:** array / object containing 24 floating-point values

**Meaning:** Hourly breakdown of observed sales across the 24 hours of the day.

**Validation / constraints:**
- Every evaluated row contained exactly 24 values.
- Sum of hourly values matched `sale_amount` for all evaluated rows.
- Stored in pandas as `numpy.ndarray`.

**SupplyGuard usage:**
- Intraday demand analysis.
- Stockout-censoring investigation.
- Potential demand reconstruction research.
- Not expected to remain as a nested field in the final analytical model.

---

### stock_hour6_22_cnt

**Type:** integer

**Meaning:** Number of out-of-stock hours in the 06:00–22:00 operating window.

**Validation / constraints:**
- Values range from 0 to 16.
- No missing values found.
- Validated against `hours_stock_status[6:22]` with a 100% match across 4.5 million training records.

**SupplyGuard usage:**
- Stockout severity.
- Availability analysis.
- Censored-demand detection.
- Potential stockout-risk features.

---

### hours_stock_status

**Type:** array / object containing 24 integer values

**Meaning:** Hourly out-of-stock indicator.

**Known values:**
- `0` = not marked out of stock
- `1` = out of stock

**Validation / constraints:**
- Every evaluated row contained exactly 24 values.
- Only 0 and 1 were observed.
- Operating-window count perfectly matched `stock_hour6_22_cnt`.

**SupplyGuard usage:**
- Intraday stockout analysis.
- Demand censoring.
- Potential reconstruction of unconstrained demand.
- May later be normalised into hourly records if justified.

---

### discount

**Type:** float

**Meaning:** Discount or price-adjustment indicator/value associated with the observation.

**Validation / constraints:**
- No missing values found.
- Exact numerical interpretation should be confirmed from source documentation before using as a model feature.

**SupplyGuard usage:**
- Potential promotion/price-effect feature.
- Demand modelling.
- Requires semantic confirmation before modelling.

---

### holiday_flag

**Type:** integer

**Meaning:** Indicator for whether the date is associated with a holiday.

**Validation / constraints:**
- No missing values found.
- Expected to behave as a binary/categorical flag.

**SupplyGuard usage:**
- Temporal demand features.
- Holiday-effect analysis.

---

### activity_flag

**Type:** integer

**Meaning:** Indicator for promotional/activity status.

**Validation / constraints:**
- No missing values found.
- Exact source definition should be retained from dataset documentation.

**SupplyGuard usage:**
- Promotion/activity demand effects.
- Forecasting features.

---

### precpt

**Type:** float

**Meaning:** Precipitation-related weather measurement.

**Validation / constraints:**
- No missing values found.
- Units should be confirmed from source documentation.

**SupplyGuard usage:**
- Weather-demand relationship analysis.
- Candidate forecasting feature where evidence supports usefulness.

---

### avg_temperature

**Type:** float

**Meaning:** Average temperature for the relevant city/date.

**Validation / constraints:**
- No missing values found.
- Units should be confirmed from the official source documentation.

**SupplyGuard usage:**
- Weather-related demand features.
- Regional demand analysis.

---

### avg_humidity

**Type:** float

**Meaning:** Average humidity for the relevant city/date.

**Validation / constraints:**
- No missing values found.

**SupplyGuard usage:**
- Candidate weather feature.
- Included only if exploratory/model evidence supports its value.

---

### avg_wind_level

**Type:** float

**Meaning:** Average wind-level measurement for the relevant city/date.

**Validation / constraints:**
- No missing values found.
- Exact units/scale should be confirmed from source documentation.

**SupplyGuard usage:**
- Candidate weather-related feature.
- May be excluded if it has no meaningful predictive contribution.

---

## Confirmed Data Quality Findings

- Training rows: 4,500,000
- Evaluation rows: 350,000
- Unique store-product series: 50,000
- Training period: 90 consecutive days
- Evaluation period: 7 consecutive days
- Duplicate store-product-date records: 0
- Missing values in profiled fields: 0
- Invalid dates: 0
- Negative `sale_amount` values: 0
- Product-category inconsistencies: 0
- Evaluation-only store-product series: 0
- Hourly sales arrays: 24 values per row
- Hourly stock-status arrays: 24 values per row
- Daily/hourly sales inconsistencies in evaluated data: 0
- Stock-count/hourly-status inconsistencies in training data: 0

## Important Analytical Finding

Approximately 44% of training store-product-day observations experienced at least one out-of-stock hour during the 06:00–22:00 operating window.

Observed sales were not monotonically lower with increasing stockout duration:

- short stockouts were associated with relatively high observed sales, which may be consistent with strong demand depleting inventory;
- severe 13–16-hour stockouts showed sharply suppressed observed sales;
- severe stockout days had a zero-sales rate of approximately 54.5%.

This indicates that `sale_amount` can represent censored demand when inventory availability constrains sales.

Observed sales should therefore not automatically be treated as unconstrained customer demand in forecasting.

## Known Dataset Limitations

1. Only 90 historical training days are available per series.
2. Annual seasonality cannot be estimated reliably.
3. The source contains downstream retail demand and stockout behaviour but no supplier master, purchase orders, receipts or upstream procurement history.
4. Supplier/procurement data required by SupplyGuard will therefore be generated later using explicitly documented synthetic operational assumptions.
5. Some field semantics and units, particularly weather and promotional fields, should be confirmed against the official source documentation before feature engineering.
6. The dataset represents retail-store demand rather than a complete wholesaler operating system.

## Current SupplyGuard Data Strategy

FreshRetailNet-50K will serve as the real downstream demand and stock-availability backbone.

A synthetic upstream operational layer will later add:

- suppliers;
- supplier-product relationships;
- supplier lead-time history;
- purchase orders;
- promised delivery dates;
- actual receipt dates;
- inventory cost;
- replenishment events;
- distribution-centre inventory;
- supplier reliability behaviour.

Synthetic data will always be explicitly labelled as synthetic and generated from documented business rules rather than presented as real company data.