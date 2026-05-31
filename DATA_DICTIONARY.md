# Weekly Transportation Network Control Tower: Data Dictionary

## 1. Conventions

### 1.1 General Rules

| Rule | Definition |
|---|---|
| Date format | ISO 8601: `YYYY-MM-DD` |
| Currency | USD |
| Distance | Miles |
| Time | Hours |
| Emissions | Kilograms of CO2 equivalent (`kg CO2e`) |
| Week start | Monday |
| Raw data grain | Daily by entity unless otherwise stated |
| Null handling | Use `NULL` when a value is unknown or a denominator is zero |
| Identifier style | Uppercase prefixes with underscores, such as `DS_BEL_01` |

### 1.2 Entity Prefixes

| Prefix | Meaning |
|---|---|
| `FC` | Fulfillment Center |
| `SC` | Sort Center |
| `DS` | Delivery Station |

### 1.3 Metric Classifications

| Classification | Definition |
|---|---|
| `STANDARD_KPI` | Metric calculated directly from raw data using documented aggregation logic |
| `PLANNING_SIGNAL` | Derived business rule or composite score used to prioritize investigation |
| `SCENARIO_OUTPUT` | Projected metric calculated after applying a user-defined planning action |

---

## 2. Raw Tables

## 2.1 `dim_nodes`

**Purpose:** Stores the master data for network facilities.

**Grain:** One row per node.

**Primary key:** `node_id`

| Column | Type | Nullable | Example | Definition |
|---|---|---:|---|---|
| `node_id` | `TEXT` | No | `DS_BEL_01` | Unique facility identifier |
| `node_name` | `TEXT` | No | `Bellevue Delivery Station 01` | Human-readable facility name |
| `node_type` | `TEXT` | No | `DS` | Facility type: `FC`, `SC`, or `DS` |
| `region` | `TEXT` | No | `PACIFIC_NORTHWEST` | Planning region |
| `city` | `TEXT` | No | `Bellevue` | Facility city |
| `state_code` | `TEXT` | No | `WA` | Two-letter US state code |
| `latitude` | `REAL` | No | `47.6101` | Facility latitude for mapping |
| `longitude` | `REAL` | No | `-122.2015` | Facility longitude for mapping |
| `default_daily_capacity_packages` | `INTEGER` | No | `18500` | Standard daily processing capacity |
| `active_flag` | `INTEGER` | No | `1` | `1` if active, otherwise `0` |
| `effective_start_date` | `DATE` | No | `2026-01-01` | First date the record is valid |
| `effective_end_date` | `DATE` | Yes | `NULL` | Last valid date; `NULL` indicates current |

## 2.2 `dim_lanes`

**Purpose:** Stores lane master data and the attributes required for service, cost, and emissions analysis.

**Grain:** One row per directed lane.

**Primary key:** `lane_id`

| Column | Type | Nullable | Example | Definition |
|---|---|---:|---|---|
| `lane_id` | `TEXT` | No | `SC_SEA_01__DS_BEL_01` | Unique directed lane identifier |
| `origin_node_id` | `TEXT` | No | `SC_SEA_01` | Origin facility; foreign key to `dim_nodes.node_id` |
| `destination_node_id` | `TEXT` | No | `DS_BEL_01` | Destination facility; foreign key to `dim_nodes.node_id` |
| `lane_type` | `TEXT` | No | `SC_TO_DS` | Lane category: `FC_TO_SC` or `SC_TO_DS` |
| `transport_mode` | `TEXT` | No | `GROUND` | Transportation mode, such as `GROUND` or `EXPEDITED_GROUND` |
| `distance_miles` | `REAL` | No | `21.4` | One-way distance traveled per trip |
| `planned_transit_hours` | `REAL` | No | `2.0` | Standard planned transit time |
| `vehicle_type` | `TEXT` | No | `MEDIUM_TRUCK` | Vehicle category |
| `vehicle_capacity_packages` | `INTEGER` | No | `1800` | Maximum packages per trip |
| `emission_factor_kg_co2e_per_mile` | `REAL` | No | `1.35` | Estimated vehicle emissions per mile |
| `base_cost_usd_per_trip` | `REAL` | No | `630.00` | Standard trip cost used to generate and validate movement data |
| `active_flag` | `INTEGER` | No | `1` | `1` if active, otherwise `0` |

## 2.3 `fact_lane_movements`

**Purpose:** Stores actual and planned daily transportation activity. This is the primary source for lane service, cost, and emissions KPIs.

**Grain:** One row per movement date and lane.

**Primary key:** (`movement_date`, `lane_id`)

| Column | Type | Nullable | Example | Definition |
|---|---|---:|---|---|
| `movement_date` | `DATE` | No | `2026-04-20` | Date the movement occurred |
| `lane_id` | `TEXT` | No | `SC_SEA_01__DS_BEL_01` | Lane identifier; foreign key to `dim_lanes.lane_id` |
| `planned_packages` | `INTEGER` | No | `1470` | Packages expected to move on the lane |
| `packages_shipped` | `INTEGER` | No | `1540` | Packages actually moved on the lane |
| `trips_planned` | `INTEGER` | No | `1` | Planned vehicle trips |
| `trips_completed` | `INTEGER` | No | `1` | Completed vehicle trips |
| `transport_cost_usd` | `REAL` | No | `630.00` | Actual transportation cost |
| `actual_transit_hours` | `REAL` | No | `2.8` | Average actual transit time weighted across trips |
| `late_packages` | `INTEGER` | No | `135` | Packages that missed the service promise due to lane or downstream operational performance |
| `exception_packages` | `INTEGER` | No | `44` | Packages associated with a documented transportation exception |
| `expedited_packages` | `INTEGER` | No | `0` | Packages moved using an expedited service |

**Validation rules:**

- `packages_shipped >= 0`
- `planned_packages >= 0`
- `trips_completed >= 0`
- `late_packages BETWEEN 0 AND packages_shipped`
- `exception_packages BETWEEN 0 AND packages_shipped`
- `expedited_packages BETWEEN 0 AND packages_shipped`

## 2.4 `fact_node_operations`

**Purpose:** Stores actual and planned daily node processing activity. This is the primary source for node capacity and operational exception analysis.

**Grain:** One row per operation date and node.

**Primary key:** (`operation_date`, `node_id`)

| Column | Type | Nullable | Example | Definition |
|---|---|---:|---|---|
| `operation_date` | `DATE` | No | `2026-04-20` | Date of facility operations |
| `node_id` | `TEXT` | No | `DS_BEL_01` | Facility identifier; foreign key to `dim_nodes.node_id` |
| `planned_volume` | `INTEGER` | No | `17500` | Expected packages to process |
| `packages_processed` | `INTEGER` | No | `19800` | Actual packages processed |
| `available_capacity_packages` | `INTEGER` | No | `18500` | Capacity available on the specific day after known constraints |
| `late_packages` | `INTEGER` | No | `880` | Processed packages that missed the service promise |
| `exception_packages` | `INTEGER` | No | `310` | Processed packages associated with an operational exception |
| `labor_hours` | `REAL` | No | `1240.0` | Labor hours used during the operating day |
| `downtime_hours` | `REAL` | No | `0.5` | Hours of operational downtime |

**Validation rules:**

- All package counts must be non-negative.
- `late_packages <= packages_processed`
- `exception_packages <= packages_processed`
- `available_capacity_packages >= 0`
- `labor_hours >= 0`
- `downtime_hours BETWEEN 0 AND 24`

---

## 3. SQL Transformation Views

All dashboard KPIs must be derived through SQL views. The application layer may filter and visualize view output but should not redefine metric formulas.

### 3.1 SQLite Week Start Expression

Use the following expression consistently to map each date to its Monday week start:

```sql
DATE(date_column, '-' || ((CAST(strftime('%w', date_column) AS INTEGER) + 6) % 7) || ' days')
```

### 3.2 `vw_weekly_network_kpis`

**Purpose:** Supports Executive Overview KPI cards and trends.

**Grain:** One row per `week_start` and `region`.

| Column | Definition |
|---|---|
| `week_start` | Monday date representing the planning week |
| `region` | Planning region |
| `total_packages_shipped` | Sum of lane packages shipped |
| `late_packages` | Sum of late lane packages |
| `on_time_delivery_rate` | `1 - late_packages / total_packages_shipped` |
| `transport_cost_usd` | Total actual transportation cost |
| `cost_per_package_usd` | Transportation cost divided by packages shipped |
| `co2e_kg` | Movement-level emissions aggregated to week and region |
| `co2e_kg_per_package` | Total emissions divided by packages shipped |
| `exception_packages` | Total packages with transportation exceptions |
| `exception_rate` | Exception packages divided by packages shipped |

**Representative SQL:**

```sql
CREATE VIEW vw_weekly_network_kpis AS
SELECT
    DATE(
        m.movement_date,
        '-' || ((CAST(strftime('%w', m.movement_date) AS INTEGER) + 6) % 7) || ' days'
    ) AS week_start,
    origin.region,
    SUM(m.packages_shipped) AS total_packages_shipped,
    SUM(m.late_packages) AS late_packages,
    1.0 - 1.0 * SUM(m.late_packages) / NULLIF(SUM(m.packages_shipped), 0)
        AS on_time_delivery_rate,
    SUM(m.transport_cost_usd) AS transport_cost_usd,
    1.0 * SUM(m.transport_cost_usd) / NULLIF(SUM(m.packages_shipped), 0)
        AS cost_per_package_usd,
    SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile)
        AS co2e_kg,
    1.0 * SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile)
        / NULLIF(SUM(m.packages_shipped), 0) AS co2e_kg_per_package,
    SUM(m.exception_packages) AS exception_packages,
    1.0 * SUM(m.exception_packages) / NULLIF(SUM(m.packages_shipped), 0)
        AS exception_rate
FROM fact_lane_movements m
JOIN dim_lanes l
    ON m.lane_id = l.lane_id
JOIN dim_nodes origin
    ON l.origin_node_id = origin.node_id
GROUP BY week_start, origin.region;
```

### 3.3 `vw_weekly_node_performance`

**Purpose:** Supports capacity monitoring and node-level root cause analysis.

**Grain:** One row per `week_start` and `node_id`.

| Column | Definition |
|---|---|
| `week_start` | Monday date representing the planning week |
| `node_id` | Facility identifier |
| `node_type` | Facility type |
| `region` | Planning region |
| `planned_volume` | Sum of daily planned volume |
| `packages_processed` | Sum of daily actual processed packages |
| `available_capacity_packages` | Sum of daily available capacity |
| `capacity_utilization` | Packages processed divided by available capacity |
| `volume_deviation_vs_plan` | `(actual volume - planned volume) / planned volume` |
| `late_packages` | Sum of late packages |
| `on_time_delivery_rate` | `1 - late packages / packages processed` |
| `exception_packages` | Sum of packages with operational exceptions |
| `exception_rate` | Exception packages divided by packages processed |
| `labor_hours` | Total labor hours |
| `packages_per_labor_hour` | Packages processed divided by labor hours |
| `downtime_hours` | Total downtime hours |

### 3.4 `vw_weekly_lane_performance`

**Purpose:** Supports lane-level root cause analysis, cost leakage detection, and scenario planning.

**Grain:** One row per `week_start` and `lane_id`.

| Column | Definition |
|---|---|
| `week_start` | Monday date representing the planning week |
| `lane_id` | Lane identifier |
| `origin_node_id` | Origin facility |
| `destination_node_id` | Destination facility |
| `lane_type` | Lane category |
| `transport_mode` | Transportation mode |
| `planned_packages` | Sum of expected packages |
| `packages_shipped` | Sum of actual packages |
| `volume_deviation_vs_plan` | `(actual packages - planned packages) / planned packages` |
| `trips_completed` | Sum of completed trips |
| `transport_cost_usd` | Sum of transportation cost |
| `cost_per_package_usd` | Cost divided by packages shipped |
| `weighted_actual_transit_hours` | Package-weighted average actual transit time |
| `planned_transit_hours` | Lane master planned transit hours |
| `transit_delay_hours` | Actual weighted transit time minus planned transit time |
| `late_packages` | Sum of late packages |
| `on_time_delivery_rate` | `1 - late packages / packages shipped` |
| `exception_packages` | Sum of packages with transportation exceptions |
| `exception_rate` | Exception packages divided by packages shipped |
| `co2e_kg` | `distance * completed trips * emission factor` |
| `co2e_kg_per_package` | Emissions divided by packages shipped |

### 3.5 `vw_root_cause_signals`

**Purpose:** Applies transparent planning rules to weekly node and lane metrics.

**Grain:** One row per `week_start`, `entity_type`, `entity_id`, and `signal_code`.

| Column | Definition |
|---|---|
| `week_start` | Monday date representing the planning week |
| `entity_type` | `NODE` or `LANE` |
| `entity_id` | Node or lane identifier |
| `signal_code` | Stable rule identifier |
| `signal_name` | Human-readable signal name |
| `severity` | `LOW`, `MEDIUM`, or `HIGH` |
| `observed_value` | Metric value that triggered the rule |
| `threshold_value` | Threshold used by the rule |
| `business_message` | Plain-English interpretation |
| `recommended_action` | Suggested planning response |

**Initial rules:**

| Signal Code | Entity | Condition | Interpretation |
|---|---|---|---|
| `NODE_CAPACITY_PRESSURE` | Node | `capacity_utilization > 0.95` | Node is near or above available capacity |
| `NODE_VOLUME_SPIKE` | Node | `volume_deviation_vs_plan > 0.10` | Actual node volume materially exceeded plan |
| `NODE_EXCEPTION_RATE_HIGH` | Node | `exception_rate > 0.03` | Operational exceptions require investigation |
| `LANE_TRANSIT_DELAY` | Lane | `transit_delay_hours > 1.0` | Lane transit performance declined |
| `LANE_COST_LEAKAGE` | Lane | Elevated `cost_per_package_usd` and no material service improvement | Higher cost may not be justified by service |
| `LANE_VOLUME_SPIKE` | Lane | `volume_deviation_vs_plan > 0.10` | Actual lane volume exceeded plan |

### 3.6 `vw_metric_dictionary`

**Purpose:** Powers the Data & Metric Catalog page.

**Grain:** One row per metric.

This may be implemented as a SQL view over a small metadata table named `metric_dictionary`.

| Column | Definition |
|---|---|
| `metric_id` | Stable machine-readable identifier |
| `metric_name` | Human-readable dashboard name |
| `metric_classification` | `STANDARD_KPI`, `PLANNING_SIGNAL`, or `SCENARIO_OUTPUT` |
| `business_definition` | Plain-English definition |
| `formula_display` | Formula shown in the dashboard |
| `source_tables` | Comma-separated source tables |
| `source_columns` | Comma-separated source columns |
| `sql_view_name` | SQL view that provides the metric |
| `data_grain` | Aggregation level |
| `refresh_cadence` | `WEEKLY` for the MVP |
| `decision_use_case` | How a planner should use the metric |

---

## 4. KPI Catalog

## 4.1 Standard KPIs

| Metric ID | Dashboard Name | Formula | Primary SQL View | Decision Use Case |
|---|---|---|---|---|
| `total_packages_shipped` | Total Packages Shipped | `SUM(packages_shipped)` | `vw_weekly_network_kpis` | Understand network workload |
| `late_packages` | Late Packages | `SUM(late_packages)` | `vw_weekly_network_kpis` | Quantify service misses |
| `on_time_delivery_rate` | On-Time Delivery Rate | `1 - SUM(late_packages) / SUM(packages_shipped)` | `vw_weekly_network_kpis` | Track customer promise performance |
| `transport_cost_usd` | Transportation Cost | `SUM(transport_cost_usd)` | `vw_weekly_network_kpis` | Track total spend |
| `cost_per_package_usd` | Cost per Package | `SUM(transport_cost_usd) / SUM(packages_shipped)` | `vw_weekly_network_kpis` | Compare cost efficiency across weeks and lanes |
| `co2e_kg` | Total CO2e | `SUM(distance_miles * trips_completed * emission_factor)` | `vw_weekly_network_kpis` | Track total estimated transportation emissions |
| `co2e_kg_per_package` | CO2e per Package | `Total CO2e / SUM(packages_shipped)` | `vw_weekly_network_kpis` | Compare emissions efficiency while controlling for volume |
| `capacity_utilization` | Capacity Utilization | `SUM(packages_processed) / SUM(available_capacity_packages)` | `vw_weekly_node_performance` | Identify nodes approaching overload |
| `volume_deviation_vs_plan` | Volume Deviation vs Plan | `(SUM(actual) - SUM(planned)) / SUM(planned)` | Node and lane views | Identify demand or execution variance |
| `exception_rate` | Exception Rate | `SUM(exception_packages) / SUM(packages)` | Network, node, and lane views | Quantify operational instability |
| `transit_delay_hours` | Transit Delay Hours | `Weighted Actual Transit Hours - Planned Transit Hours` | `vw_weekly_lane_performance` | Identify lane disruptions |
| `packages_per_labor_hour` | Packages per Labor Hour | `SUM(packages_processed) / SUM(labor_hours)` | `vw_weekly_node_performance` | Monitor node productivity |

## 4.2 Planning Signals

Planning signals are transparent prioritization rules. They are not presented as industry-standard metrics.

| Metric ID | Dashboard Name | Formula or Rule | Decision Use Case |
|---|---|---|---|
| `late_package_contribution_pct` | Late Package Contribution | `Entity Late Packages / Network Late Packages` | Prioritize the nodes and lanes with the largest impact |
| `capacity_risk_level` | Capacity Risk Level | `HIGH` if utilization `> 100%`; `MEDIUM` if `> 95%`; otherwise `LOW` | Focus weekly capacity reviews |
| `cost_leakage_flag` | Cost Leakage Flag | Flag higher-cost lanes without material service improvement | Identify reallocation candidates |
| `root_cause_signal_count` | Root Cause Signal Count | Count triggered rules per entity | Rank entities requiring investigation |

## 4.3 Scenario Outputs

| Metric ID | Dashboard Name | Formula | Decision Use Case |
|---|---|---|---|
| `projected_lane_volume` | Projected Lane Volume | `Baseline Lane Volume + Net Reallocated Packages` | Validate lane-level flow changes |
| `projected_node_volume` | Projected Node Volume | `Baseline Node Volume + Net Reallocated Packages` | Validate receiving-node workload |
| `projected_capacity_utilization` | Projected Capacity Utilization | `Projected Node Volume / Available Capacity` | Warn about overload risk |
| `projected_transport_cost_usd` | Projected Transportation Cost | Recalculate trips and trip costs after reallocation | Compare cost impact |
| `projected_co2e_kg` | Projected Total CO2e | Recalculate trips, distance, and emissions factors after reallocation | Compare emissions impact |
| `projected_on_time_delivery_rate` | Projected On-Time Delivery Rate | Rule-based service estimate after reallocation | Compare service trade-offs; label clearly as an estimate |

---

## 5. Carbon Emissions Methodology

### 5.1 Movement-Level Calculation

```text
Movement CO2e (kg)
= Distance Miles
* Trips Completed
* Vehicle Emission Factor (kg CO2e per mile)
```

### 5.2 Weekly Network Calculation

```text
CO2e per Package (kg)
= SUM(Movement CO2e)
/ SUM(Packages Shipped)
```

### 5.3 Interpretation

The MVP assumes each recorded trip is fully allocated to the demo transportation network. A separate allocation ratio is not required.

Vehicle load efficiency is reflected naturally: if the same vehicle trip carries more packages, total trip emissions stay constant while emissions per package decline.

### 5.4 Limitation

This is an operational estimate, not a formal lifecycle assessment. It excludes vehicle manufacturing, facility energy consumption, upstream fuel production, and last-mile delivery after the delivery station.

---

## 6. Scenario Planner Data Model

Scenario Planner calculations may be performed in Python using SQL view output as the baseline. Scenario outputs must remain separate from actual historical metrics.

## 6.1 Optional `scenario_runs`

**Purpose:** Stores scenario metadata if scenario persistence is implemented.

**Grain:** One row per saved scenario.

| Column | Type | Nullable | Definition |
|---|---|---:|---|
| `scenario_id` | `TEXT` | No | Unique scenario identifier |
| `scenario_name` | `TEXT` | No | User-facing scenario name |
| `planning_week_start` | `DATE` | No | Monday of the evaluated week |
| `created_at` | `TIMESTAMP` | No | Scenario creation timestamp |
| `scenario_status` | `TEXT` | No | `DRAFT` or `SAVED` |
| `notes` | `TEXT` | Yes | Optional user notes |

## 6.2 Optional `scenario_lane_reallocations`

**Purpose:** Stores user-defined lane volume changes.

**Grain:** One row per scenario and lane.

| Column | Type | Nullable | Definition |
|---|---|---:|---|
| `scenario_id` | `TEXT` | No | Foreign key to `scenario_runs.scenario_id` |
| `lane_id` | `TEXT` | No | Foreign key to `dim_lanes.lane_id` |
| `package_delta` | `INTEGER` | No | Positive for added packages, negative for removed packages |
| `available_capacity_override` | `INTEGER` | Yes | Optional scenario-only receiving capacity |
| `cost_usd_per_trip_override` | `REAL` | Yes | Optional scenario-only trip cost |
| `transit_delay_hours_override` | `REAL` | Yes | Optional scenario-only delay adjustment |
| `reason_code` | `TEXT` | No | `CAPACITY_PRESSURE`, `LANE_DISRUPTION`, `COST_LEAKAGE`, or `MANUAL_TEST` |

**Validation rules:**

- Package deltas across a scenario must sum to zero.
- Projected lane package counts must not be negative.
- Overrides apply only to the scenario and never overwrite raw historical data.

---

## 7. Data Quality Checks

| Check ID | Table | Rule | Response |
|---|---|---|---|
| `DQ_001` | `fact_lane_movements` | Late packages cannot exceed shipped packages | Reject row |
| `DQ_002` | `fact_lane_movements` | Exception packages cannot exceed shipped packages | Reject row |
| `DQ_003` | `fact_lane_movements` | Lane identifier must exist in `dim_lanes` | Reject row |
| `DQ_004` | `fact_node_operations` | Node identifier must exist in `dim_nodes` | Reject row |
| `DQ_005` | `fact_node_operations` | Late packages cannot exceed processed packages | Reject row |
| `DQ_006` | `dim_lanes` | Origin and destination nodes must exist in `dim_nodes` | Reject row |
| `DQ_007` | SQL metric layer | KPI denominator must not be zero | Return `NULL` |
| `DQ_008` | Scenario Planner | Reallocation deltas must sum to zero | Block scenario comparison |
| `DQ_009` | Scenario Planner | Projected lane packages cannot be negative | Block scenario comparison |
| `DQ_010` | Scenario Planner | Total packages must remain unchanged | Block scenario comparison |

---

## 8. Seeded Demo Exceptions

| Exception | Raw Data Pattern | Expected KPI Impact | Expected Planning Signal |
|---|---|---|---|
| Capacity Pressure | Increase `packages_processed` above available capacity at one `DS` | Lower OTD, higher utilization, higher exception rate | `NODE_CAPACITY_PRESSURE`, `NODE_VOLUME_SPIKE` |
| Lane Disruption | Increase `actual_transit_hours` and `late_packages` on one `SC_TO_DS` lane | Higher transit delay and late package contribution | `LANE_TRANSIT_DELAY` |
| Cost Leakage | Increase trip count or use `EXPEDITED_GROUND` without material OTD improvement | Higher cost per package | `LANE_COST_LEAKAGE` |

---

## 9. Implementation Notes

- Generate raw data first, then calculate KPI views through SQL.
- Keep raw tables free of pre-calculated KPI percentages.
- Use package-weighted averages for lane transit time.
- Calculate emissions at lane movement grain before weekly aggregation.
- Keep historical actuals and scenario projections visually distinct in the dashboard.
- Surface SQL definitions in the Data & Metric Catalog to make metric lineage visible.
