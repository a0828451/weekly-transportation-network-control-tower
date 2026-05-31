# Coding Prompt: Weekly Transportation Network Control Tower

Build a portfolio-grade Streamlit MVP named **Weekly Transportation Network Control Tower**.

Use the accompanying `PRD.md` and `DATA_DICTIONARY.md` as the source of truth. The application should demonstrate the work of a Supply Chain Manager conducting weekly outbound transportation network planning. Prioritize KPI governance, SQL traceability, dashboard usability, root cause investigation, and operational decision-making. Do not add machine learning or route optimization.

## Required Stack

- Python
- pandas
- SQLite
- Streamlit
- Plotly
- Python standard-library `unittest`

## Architecture

```text
Raw SQLite tables
  -> SQL metric views
  -> Python query helpers
  -> Streamlit dashboard
```

KPI formulas must be defined in SQL views. Do not hard-code historical dashboard KPI values in the Streamlit layer.

## Required Features

1. Generate a deterministic demo dataset with 3 fulfillment centers, 4 sort centers, 8 delivery stations, 12 weeks of daily data, and three seeded exceptions:
   - Delivery station capacity pressure
   - Sort-center-to-delivery-station lane disruption
   - Expedited lane cost leakage
2. Create the raw tables and SQL metric-layer views documented in `DATA_DICTIONARY.md`.
3. Build four English-language dashboard pages:
   - Executive Overview
   - Root Cause Deep Dive
   - Scenario Planner
   - Data & Metric Catalog
4. Support weekly lane volume reallocation scenarios. Preserve total package count, reject invalid source volumes, warn when receiving-node capacity is exceeded, and clearly label service projections as estimates.
5. Expose metric business definitions, formulas, SQL view names, and representative SQL in the catalog.
6. Add backend tests for:
   - Monday week aggregation
   - Seeded exception signals
   - Carbon KPI calculation
   - Valid reallocation package conservation
   - Invalid reallocation rejection

## UX Guidelines

- Make the interface suitable for a portfolio demo.
- Use KPI cards and concise operational summaries.
- Use Plotly for trend, Pareto, heatmap, and scenario comparison charts.
- Clearly distinguish historical actuals from projected scenario values.
- Label planning signals as transparent rules, not industry-standard KPIs.

## Deliverables

- Runnable Streamlit app
- Deterministic SQLite database generator
- SQL schema and views
- Scenario planning module
- Backend test suite
- README with setup and run instructions

