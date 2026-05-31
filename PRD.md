# Weekly Transportation Network Control Tower

## 1. Product Summary

Weekly Transportation Network Control Tower is a portfolio-grade supply chain planning dashboard for monitoring an outbound transportation network, diagnosing performance issues, and evaluating lane volume reallocation decisions.

The product is designed for a Supply Chain Manager conducting weekly network planning. It emphasizes KPI design, traceable SQL definitions, operational deep dives, and decision-making rather than advanced predictive modeling.

## 2. Problem Statement

Transportation network managers need to answer three questions quickly:

1. Where is the network underperforming?
2. What is driving the issue?
3. Which operational action offers the best trade-off across service, cost, capacity, and carbon emissions?

Raw operational data alone does not answer these questions. The product must translate lane and node-level data into consistent weekly metrics, highlight actionable exceptions, and allow planners to compare reallocation scenarios.

## 3. Target User

**Primary user:** Supply Chain Manager responsible for weekly outbound transportation network planning.

**User responsibilities:**

- Review network performance against targets and prior periods.
- Identify capacity, service, cost, and emissions risks.
- Conduct node and lane-level root cause analysis.
- Reallocate lane volume during disruptions or demand changes.
- Communicate recommended actions with clear supporting evidence.

## 4. Product Goals

- Provide a weekly executive view of network health.
- Make every dashboard KPI traceable to raw data and SQL logic.
- Surface the nodes and lanes contributing most to service failures.
- Support lane volume reallocation scenarios without requiring an optimization model.
- Compare baseline and proposed scenarios across business trade-offs.
- Demonstrate practical SQL, dashboarding, and supply chain decision-making skills.

## 5. Out of Scope for MVP

- Machine learning forecasting.
- Route-level vehicle dispatch optimization.
- Real-time streaming data.
- Package-level customer delivery tracking.
- Automated decision execution.
- Multi-echelon inventory planning.

## 6. Network Scope

The demo dataset represents a simplified outbound network:

- 3 fulfillment centers (`FC`)
- 4 sort centers (`SC`)
- 8 delivery stations (`DS`)
- Daily raw data aggregated into weekly planning views
- 8 to 12 weeks of historical data
- Planned and actual lane movements
- Planned and actual node operations

Supported lane types:

- `FC_TO_SC`
- `SC_TO_DS`

## 7. MVP Pages

### 7.1 Executive Overview

**Purpose:** Provide a weekly summary of network health and identify areas requiring attention.

**Required components:**

- Week selector and region filter
- KPI cards with current value, target variance, and week-over-week change
- 8-week trend charts
- Network performance table by region
- Top exceptions table

**Primary KPIs:**

- On-Time Delivery Rate
- Cost per Package
- CO2 per Package
- Capacity Utilization
- Volume Deviation vs Plan
- Exception Rate
- Total Packages Shipped
- Late Packages

### 7.2 Root Cause Deep Dive

**Purpose:** Explain why service, cost, or capacity performance changed.

**Required components:**

- Node and lane filters
- Ranked node and lane contribution tables
- Late package Pareto chart
- Capacity utilization heatmap
- Planned vs actual volume trend
- Planned vs actual transit time comparison
- Rule-based root cause signals
- Management summary with recommended next steps

**Example questions:**

- Which nodes contributed most to late packages?
- Did service decline because volume exceeded plan or capacity fell?
- Which lanes experienced transit delay?
- Are expedited lanes increasing cost without improving service?

### 7.3 Scenario Planner

**Purpose:** Compare lane volume reallocation actions for weekly planning.

**User inputs:**

- Planning week
- Source lane
- Destination lane
- Number of packages to reallocate
- Optional available capacity override
- Optional transport cost override
- Optional transit delay override

**Validation rules:**

- Reallocated packages cannot exceed the source lane volume.
- Destination node projected volume cannot exceed available capacity without displaying an overload warning.
- Source and destination lanes must be valid alternatives serving the same planning region.
- Scenario results must preserve the total number of packages in scope.

**Required outputs:**

- Baseline vs proposed KPI comparison
- Projected node utilization
- Projected lane volume
- Service, cost, and emissions impact
- Overloaded node warnings
- Plain-English action summary

### 7.4 Data & Metric Catalog

**Purpose:** Make metric definitions transparent and demonstrate SQL-based data preparation.

**Required components:**

- Searchable metric list
- Business definition
- Formula
- Source tables and columns
- Data grain
- Refresh cadence
- SQL view name
- SQL definition or representative SQL query
- Metric classification

Metric classifications:

- `STANDARD_KPI`: directly aggregated from raw data
- `PLANNING_SIGNAL`: derived business rule used to prioritize investigation

## 8. Data Architecture

```text
Raw Tables
  dim_nodes
  dim_lanes
  fact_lane_movements
  fact_node_operations
        |
        v
SQL Metric Layer
  vw_weekly_network_kpis
  vw_weekly_node_performance
  vw_weekly_lane_performance
  vw_root_cause_signals
  vw_metric_dictionary
        |
        v
Streamlit Dashboard
  Executive Overview
  Root Cause Deep Dive
  Scenario Planner
  Data & Metric Catalog
```

SQLite is sufficient for the MVP. SQL views must calculate dashboard KPIs from raw tables; KPI values should not be hard-coded in the application layer.

## 9. Required Demo Scenarios

### Scenario A: Capacity Pressure

- A delivery station receives higher-than-planned volume.
- Capacity utilization exceeds target.
- On-time delivery declines and exception rate increases.
- Recommended action: reallocate eligible lane volume to a nearby delivery station with available capacity.

### Scenario B: Lane Disruption

- A sort-center-to-delivery-station lane experiences increased transit time.
- Late package contribution is concentrated in the affected lane.
- Recommended action: redirect eligible volume through an alternate lane or add temporary capacity.

### Scenario C: Cost Leakage

- An expedited lane has elevated cost per package.
- Service performance is not materially better than a standard lane.
- Recommended action: shift eligible volume to the lower-cost lane while monitoring service risk.

## 10. KPI Governance Principles

- Every KPI must have one documented business definition.
- Weekly metrics must use a consistent week start date: Monday.
- Weighted averages must use the correct operational denominator.
- Division by zero must return `NULL`, not an arbitrary value.
- Carbon emissions must be calculated at movement level before aggregation.
- Planning signals must be labeled as derived rules, not industry-standard metrics.
- Scenario KPIs must be clearly labeled as projected values.

## 11. MVP Acceptance Criteria

- The dashboard reads raw operational data from SQLite.
- SQL views calculate all Executive Overview KPI cards.
- Users can drill from network-level KPIs to node and lane-level evidence.
- At least three seeded exceptions produce understandable root cause signals.
- Users can reallocate lane volume and compare baseline vs proposed results.
- The Scenario Planner warns users about invalid moves and capacity overloads.
- The Data & Metric Catalog documents the source and SQL logic for every displayed KPI.
- The full dashboard interface is written in English.

## 12. Suggested Technology Stack

- Python
- pandas
- SQLite
- Streamlit
- Plotly
- pytest

