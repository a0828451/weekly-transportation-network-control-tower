# Weekly Transportation Network Control Tower


A Streamlit portfolio project for weekly outbound transportation network planning. It demonstrates SQL-defined KPI governance, operational root cause analysis, and multi-action lane volume reallocation decisions.

The dashboard is designed around a Supply Chain Manager workflow:

1. Identify a weekly service or capacity exception.
2. Trace the issue to contributing nodes and lanes.
3. Compare reallocation actions across service, cost, capacity, and CO2e trade-offs.
4. Surface residual risks that still require mitigation.
   
## Live Demo
[Open the interactive dashboard](https://weekly-transportation-network-control-tower.streamlit.app/)

## Features

- Executive KPI overview with weekly trends
- Node and lane-level root cause deep dives
- Transparent rule-based planning signals
- Multi-action lane volume reallocation scenario comparison
- Residual capacity-risk summary after reallocation
- Risk-oriented executive KPIs, including max node utilization and nodes over capacity
- Searchable Data & Metric Catalog with SQL lineage
- Deterministic demo data with three seeded operational exceptions

## Demo Decision Workflow

The seeded dataset includes a Pacific Northwest planning exception for the week of `2026-05-18`:

- Network OTD declines to approximately `96%`.
- `DS_BEL_01` exceeds weekly processing capacity.
- `SC_SEA_01__DS_BEL_01` experiences a transit delay.

Use the Scenario Planner to redirect eligible Bellevue volume to Tacoma and Everett. The dashboard recalculates affected lane trips, transportation cost, estimated SC-to-DS OTD, CO2e, projected node utilization, and remaining capacity risk.

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m control_tower.database
streamlit run app.py
```

The app also initializes the SQLite demo database automatically if it does not exist.

## Run Backend Tests

```powershell
python -m unittest discover -s tests -v
```

## Project Structure

```text
app.py                         Streamlit interface
control_tower/database.py      SQLite schema, views, and deterministic seed data
control_tower/queries.py       Read-only dashboard query helpers
control_tower/scenario.py      Lane reallocation calculation logic
tests/                         Backend tests
PRD.md                         Product requirements
DATA_DICTIONARY.md             Raw data and KPI definitions
CODING_PROMPT.md               Reusable implementation prompt
```

## Metric Governance

Dashboard metrics are calculated by SQLite views over daily raw tables. The application layer filters and displays view output but does not redefine historical KPI formulas. Scenario outputs are calculated separately and labeled as projections.

Historical Executive Overview OTD is a network-level metric. Scenario Planner OTD is an estimated `SC_TO_DS` lane-level metric and is labeled separately in the interface.
