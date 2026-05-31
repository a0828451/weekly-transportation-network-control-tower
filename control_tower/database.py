from __future__ import annotations

import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "control_tower.db"
LATEST_WEEK = date(2026, 5, 18)
START_DATE = LATEST_WEEK - timedelta(weeks=11)

NODES = [
    ("FC_SEA_01", "Seattle Fulfillment Center", "FC", "PACIFIC_NORTHWEST", "Seattle", "WA", 47.6062, -122.3321, 43000),
    ("FC_PDX_01", "Portland Fulfillment Center", "FC", "PACIFIC_NORTHWEST", "Portland", "OR", 45.5152, -122.6784, 37000),
    ("FC_BOI_01", "Boise Fulfillment Center", "FC", "MOUNTAIN_NORTHWEST", "Boise", "ID", 43.6150, -116.2023, 29000),
    ("SC_SEA_01", "Seattle Sort Center", "SC", "PACIFIC_NORTHWEST", "Seattle", "WA", 47.6205, -122.3493, 36000),
    ("SC_PDX_01", "Portland Sort Center", "SC", "PACIFIC_NORTHWEST", "Portland", "OR", 45.5231, -122.6765, 33000),
    ("SC_GEG_01", "Spokane Sort Center", "SC", "PACIFIC_NORTHWEST", "Spokane", "WA", 47.6588, -117.4260, 24000),
    ("SC_BOI_01", "Boise Sort Center", "SC", "MOUNTAIN_NORTHWEST", "Boise", "ID", 43.6166, -116.2009, 22000),
    ("DS_BEL_01", "Bellevue Delivery Station", "DS", "PACIFIC_NORTHWEST", "Bellevue", "WA", 47.6101, -122.2015, 9500),
    ("DS_TAC_01", "Tacoma Delivery Station", "DS", "PACIFIC_NORTHWEST", "Tacoma", "WA", 47.2529, -122.4443, 9000),
    ("DS_EVE_01", "Everett Delivery Station", "DS", "PACIFIC_NORTHWEST", "Everett", "WA", 47.9790, -122.2021, 7600),
    ("DS_PDX_01", "Portland Delivery Station", "DS", "PACIFIC_NORTHWEST", "Portland", "OR", 45.5152, -122.6784, 9800),
    ("DS_SLM_01", "Salem Delivery Station", "DS", "PACIFIC_NORTHWEST", "Salem", "OR", 44.9429, -123.0351, 6800),
    ("DS_GEG_01", "Spokane Delivery Station", "DS", "PACIFIC_NORTHWEST", "Spokane", "WA", 47.6588, -117.4260, 7000),
    ("DS_BOI_01", "Boise Delivery Station", "DS", "MOUNTAIN_NORTHWEST", "Boise", "ID", 43.6150, -116.2023, 7600),
    ("DS_NAM_01", "Nampa Delivery Station", "DS", "MOUNTAIN_NORTHWEST", "Nampa", "ID", 43.5407, -116.5635, 5600),
]

LANES = [
    ("FC_SEA_01__SC_SEA_01", "FC_SEA_01", "SC_SEA_01", "FC_TO_SC", "GROUND", 18.0, 1.2, "LINEHAUL_TRAILER", 4200, 1.85, 720.0),
    ("FC_PDX_01__SC_PDX_01", "FC_PDX_01", "SC_PDX_01", "FC_TO_SC", "GROUND", 16.0, 1.1, "LINEHAUL_TRAILER", 4200, 1.85, 690.0),
    ("FC_BOI_01__SC_BOI_01", "FC_BOI_01", "SC_BOI_01", "FC_TO_SC", "GROUND", 14.0, 1.0, "LINEHAUL_TRAILER", 4200, 1.85, 650.0),
    ("FC_SEA_01__SC_GEG_01", "FC_SEA_01", "SC_GEG_01", "FC_TO_SC", "GROUND", 279.0, 5.2, "LINEHAUL_TRAILER", 4200, 1.85, 1290.0),
    ("SC_SEA_01__DS_BEL_01", "SC_SEA_01", "DS_BEL_01", "SC_TO_DS", "GROUND", 21.4, 2.0, "MEDIUM_TRUCK", 1800, 1.35, 630.0),
    ("SC_SEA_01__DS_TAC_01", "SC_SEA_01", "DS_TAC_01", "SC_TO_DS", "GROUND", 38.0, 2.2, "MEDIUM_TRUCK", 1800, 1.35, 690.0),
    ("SC_SEA_01__DS_EVE_01", "SC_SEA_01", "DS_EVE_01", "SC_TO_DS", "GROUND", 31.0, 2.1, "MEDIUM_TRUCK", 1800, 1.35, 670.0),
    ("SC_SEA_01__DS_BEL_01_EXP", "SC_SEA_01", "DS_BEL_01", "SC_TO_DS", "EXPEDITED_GROUND", 21.4, 1.8, "MEDIUM_TRUCK", 1500, 1.35, 960.0),
    ("SC_PDX_01__DS_PDX_01", "SC_PDX_01", "DS_PDX_01", "SC_TO_DS", "GROUND", 18.0, 1.8, "MEDIUM_TRUCK", 1800, 1.35, 620.0),
    ("SC_PDX_01__DS_SLM_01", "SC_PDX_01", "DS_SLM_01", "SC_TO_DS", "GROUND", 48.0, 2.4, "MEDIUM_TRUCK", 1800, 1.35, 730.0),
    ("SC_GEG_01__DS_GEG_01", "SC_GEG_01", "DS_GEG_01", "SC_TO_DS", "GROUND", 12.0, 1.5, "MEDIUM_TRUCK", 1800, 1.35, 580.0),
    ("SC_BOI_01__DS_BOI_01", "SC_BOI_01", "DS_BOI_01", "SC_TO_DS", "GROUND", 13.0, 1.5, "MEDIUM_TRUCK", 1800, 1.35, 580.0),
    ("SC_BOI_01__DS_NAM_01", "SC_BOI_01", "DS_NAM_01", "SC_TO_DS", "GROUND", 22.0, 1.8, "MEDIUM_TRUCK", 1800, 1.35, 610.0),
]

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
CREATE TABLE dim_nodes (
    node_id TEXT PRIMARY KEY, node_name TEXT NOT NULL, node_type TEXT NOT NULL,
    region TEXT NOT NULL, city TEXT NOT NULL, state_code TEXT NOT NULL,
    latitude REAL NOT NULL, longitude REAL NOT NULL,
    default_daily_capacity_packages INTEGER NOT NULL, active_flag INTEGER NOT NULL,
    effective_start_date DATE NOT NULL, effective_end_date DATE
);
CREATE TABLE dim_lanes (
    lane_id TEXT PRIMARY KEY, origin_node_id TEXT NOT NULL, destination_node_id TEXT NOT NULL,
    lane_type TEXT NOT NULL, transport_mode TEXT NOT NULL, distance_miles REAL NOT NULL,
    planned_transit_hours REAL NOT NULL, vehicle_type TEXT NOT NULL,
    vehicle_capacity_packages INTEGER NOT NULL, emission_factor_kg_co2e_per_mile REAL NOT NULL,
    base_cost_usd_per_trip REAL NOT NULL, active_flag INTEGER NOT NULL,
    FOREIGN KEY(origin_node_id) REFERENCES dim_nodes(node_id),
    FOREIGN KEY(destination_node_id) REFERENCES dim_nodes(node_id)
);
CREATE TABLE fact_lane_movements (
    movement_date DATE NOT NULL, lane_id TEXT NOT NULL, planned_packages INTEGER NOT NULL,
    packages_shipped INTEGER NOT NULL, trips_planned INTEGER NOT NULL, trips_completed INTEGER NOT NULL,
    transport_cost_usd REAL NOT NULL, actual_transit_hours REAL NOT NULL,
    late_packages INTEGER NOT NULL, exception_packages INTEGER NOT NULL, expedited_packages INTEGER NOT NULL,
    PRIMARY KEY (movement_date, lane_id), FOREIGN KEY(lane_id) REFERENCES dim_lanes(lane_id),
    CHECK(late_packages BETWEEN 0 AND packages_shipped),
    CHECK(exception_packages BETWEEN 0 AND packages_shipped),
    CHECK(expedited_packages BETWEEN 0 AND packages_shipped)
);
CREATE TABLE fact_node_operations (
    operation_date DATE NOT NULL, node_id TEXT NOT NULL, planned_volume INTEGER NOT NULL,
    packages_processed INTEGER NOT NULL, available_capacity_packages INTEGER NOT NULL,
    late_packages INTEGER NOT NULL, exception_packages INTEGER NOT NULL,
    labor_hours REAL NOT NULL, downtime_hours REAL NOT NULL,
    PRIMARY KEY (operation_date, node_id), FOREIGN KEY(node_id) REFERENCES dim_nodes(node_id),
    CHECK(late_packages BETWEEN 0 AND packages_processed),
    CHECK(exception_packages BETWEEN 0 AND packages_processed),
    CHECK(downtime_hours BETWEEN 0 AND 24)
);
CREATE TABLE metric_dictionary (
    metric_id TEXT PRIMARY KEY, metric_name TEXT NOT NULL, metric_classification TEXT NOT NULL,
    business_definition TEXT NOT NULL, formula_display TEXT NOT NULL, source_tables TEXT NOT NULL,
    source_columns TEXT NOT NULL, sql_view_name TEXT NOT NULL, data_grain TEXT NOT NULL,
    refresh_cadence TEXT NOT NULL, decision_use_case TEXT NOT NULL, representative_sql TEXT NOT NULL
);
"""

VIEWS_SQL = """
CREATE VIEW vw_weekly_network_kpis AS
SELECT DATE(m.movement_date, '-' || ((CAST(strftime('%w', m.movement_date) AS INTEGER) + 6) % 7) || ' days') AS week_start,
       origin.region, SUM(m.packages_shipped) AS total_packages_shipped, SUM(m.late_packages) AS late_packages,
       1.0 - 1.0 * SUM(m.late_packages) / NULLIF(SUM(m.packages_shipped), 0) AS on_time_delivery_rate,
       SUM(m.transport_cost_usd) AS transport_cost_usd,
       1.0 * SUM(m.transport_cost_usd) / NULLIF(SUM(m.packages_shipped), 0) AS cost_per_package_usd,
       SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile) AS co2e_kg,
       1.0 * SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile) / NULLIF(SUM(m.packages_shipped), 0) AS co2e_kg_per_package,
       SUM(m.exception_packages) AS exception_packages,
       1.0 * SUM(m.exception_packages) / NULLIF(SUM(m.packages_shipped), 0) AS exception_rate
FROM fact_lane_movements m JOIN dim_lanes l ON m.lane_id = l.lane_id
JOIN dim_nodes origin ON l.origin_node_id = origin.node_id GROUP BY week_start, origin.region;

CREATE VIEW vw_weekly_node_performance AS
SELECT DATE(o.operation_date, '-' || ((CAST(strftime('%w', o.operation_date) AS INTEGER) + 6) % 7) || ' days') AS week_start,
       o.node_id, n.node_name, n.node_type, n.region, SUM(o.planned_volume) AS planned_volume,
       SUM(o.packages_processed) AS packages_processed, SUM(o.available_capacity_packages) AS available_capacity_packages,
       1.0 * SUM(o.packages_processed) / NULLIF(SUM(o.available_capacity_packages), 0) AS capacity_utilization,
       1.0 * (SUM(o.packages_processed) - SUM(o.planned_volume)) / NULLIF(SUM(o.planned_volume), 0) AS volume_deviation_vs_plan,
       SUM(o.late_packages) AS late_packages,
       1.0 - 1.0 * SUM(o.late_packages) / NULLIF(SUM(o.packages_processed), 0) AS on_time_delivery_rate,
       SUM(o.exception_packages) AS exception_packages,
       1.0 * SUM(o.exception_packages) / NULLIF(SUM(o.packages_processed), 0) AS exception_rate,
       SUM(o.labor_hours) AS labor_hours, 1.0 * SUM(o.packages_processed) / NULLIF(SUM(o.labor_hours), 0) AS packages_per_labor_hour,
       SUM(o.downtime_hours) AS downtime_hours
FROM fact_node_operations o JOIN dim_nodes n ON o.node_id = n.node_id GROUP BY week_start, o.node_id;

CREATE VIEW vw_weekly_lane_performance AS
SELECT DATE(m.movement_date, '-' || ((CAST(strftime('%w', m.movement_date) AS INTEGER) + 6) % 7) || ' days') AS week_start,
       m.lane_id, l.origin_node_id, l.destination_node_id, origin.region, l.lane_type, l.transport_mode,
       l.distance_miles, l.vehicle_capacity_packages, l.emission_factor_kg_co2e_per_mile, l.base_cost_usd_per_trip,
       SUM(m.planned_packages) AS planned_packages, SUM(m.packages_shipped) AS packages_shipped,
       1.0 * (SUM(m.packages_shipped) - SUM(m.planned_packages)) / NULLIF(SUM(m.planned_packages), 0) AS volume_deviation_vs_plan,
       SUM(m.trips_completed) AS trips_completed, SUM(m.transport_cost_usd) AS transport_cost_usd,
       1.0 * SUM(m.transport_cost_usd) / NULLIF(SUM(m.packages_shipped), 0) AS cost_per_package_usd,
       1.0 * SUM(m.actual_transit_hours * m.packages_shipped) / NULLIF(SUM(m.packages_shipped), 0) AS weighted_actual_transit_hours,
       l.planned_transit_hours,
       1.0 * SUM(m.actual_transit_hours * m.packages_shipped) / NULLIF(SUM(m.packages_shipped), 0) - l.planned_transit_hours AS transit_delay_hours,
       SUM(m.late_packages) AS late_packages,
       1.0 - 1.0 * SUM(m.late_packages) / NULLIF(SUM(m.packages_shipped), 0) AS on_time_delivery_rate,
       SUM(m.exception_packages) AS exception_packages,
       1.0 * SUM(m.exception_packages) / NULLIF(SUM(m.packages_shipped), 0) AS exception_rate,
       SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile) AS co2e_kg,
       1.0 * SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile) / NULLIF(SUM(m.packages_shipped), 0) AS co2e_kg_per_package
FROM fact_lane_movements m JOIN dim_lanes l ON m.lane_id = l.lane_id
JOIN dim_nodes origin ON l.origin_node_id = origin.node_id GROUP BY week_start, m.lane_id;

CREATE VIEW vw_root_cause_signals AS
SELECT week_start, 'NODE' AS entity_type, node_id AS entity_id, 'NODE_CAPACITY_PRESSURE' AS signal_code,
       'Node Capacity Pressure' AS signal_name, CASE WHEN capacity_utilization > 1 THEN 'HIGH' ELSE 'MEDIUM' END AS severity,
       capacity_utilization AS observed_value, 0.95 AS threshold_value,
       'Node utilization is near or above available capacity.' AS business_message,
       'Review eligible lane reallocation to a nearby node with available capacity.' AS recommended_action
FROM vw_weekly_node_performance WHERE capacity_utilization > 0.95
UNION ALL
SELECT week_start, 'NODE', node_id, 'NODE_VOLUME_SPIKE', 'Node Volume Spike', CASE WHEN volume_deviation_vs_plan > 0.2 THEN 'HIGH' ELSE 'MEDIUM' END,
       volume_deviation_vs_plan, 0.10, 'Actual node volume materially exceeded plan.', 'Validate demand assumptions and rebalance eligible volume.'
FROM vw_weekly_node_performance WHERE volume_deviation_vs_plan > 0.10
UNION ALL
SELECT week_start, 'NODE', node_id, 'NODE_EXCEPTION_RATE_HIGH', 'Node Exception Rate High', 'MEDIUM',
       exception_rate, 0.03, 'Operational exception rate requires investigation.', 'Review node constraints, downtime, and labor productivity.'
FROM vw_weekly_node_performance WHERE exception_rate > 0.03
UNION ALL
SELECT week_start, 'LANE', lane_id, 'LANE_TRANSIT_DELAY', 'Lane Transit Delay', CASE WHEN transit_delay_hours > 2 THEN 'HIGH' ELSE 'MEDIUM' END,
       transit_delay_hours, 1.0, 'Lane transit time is materially above plan.', 'Evaluate alternate lane flow or temporary capacity.'
FROM vw_weekly_lane_performance WHERE transit_delay_hours > 1.0
UNION ALL
SELECT week_start, 'LANE', lane_id, 'LANE_VOLUME_SPIKE', 'Lane Volume Spike', 'MEDIUM',
       volume_deviation_vs_plan, 0.10, 'Actual lane volume materially exceeded plan.', 'Confirm lane capacity and evaluate reallocation.'
FROM vw_weekly_lane_performance WHERE volume_deviation_vs_plan > 0.10
UNION ALL
SELECT week_start, 'LANE', lane_id, 'LANE_COST_LEAKAGE', 'Lane Cost Leakage', 'MEDIUM',
       cost_per_package_usd, 0.70, 'Higher lane cost may not be justified by service performance.', 'Compare standard lane alternatives and reallocate eligible volume.'
FROM vw_weekly_lane_performance WHERE transport_mode = 'EXPEDITED_GROUND' AND cost_per_package_usd > 0.70 AND on_time_delivery_rate < 0.98;

CREATE VIEW vw_metric_dictionary AS SELECT * FROM metric_dictionary;
"""

METRICS = [
    ("total_packages_shipped", "Total Packages Shipped", "STANDARD_KPI", "Packages transported during the selected week.", "SUM(packages_shipped)", "fact_lane_movements", "packages_shipped", "vw_weekly_network_kpis", "Week and region", "WEEKLY", "Understand network workload.", "SELECT SUM(packages_shipped) FROM fact_lane_movements;"),
    ("on_time_delivery_rate", "On-Time Delivery Rate", "STANDARD_KPI", "Share of shipped packages that did not miss the service promise.", "1 - SUM(late_packages) / SUM(packages_shipped)", "fact_lane_movements", "late_packages, packages_shipped", "vw_weekly_network_kpis", "Week and region", "WEEKLY", "Track customer promise performance.", "SELECT 1.0 - 1.0 * SUM(late_packages) / NULLIF(SUM(packages_shipped), 0) FROM fact_lane_movements;"),
    ("cost_per_package_usd", "Cost per Package", "STANDARD_KPI", "Transportation spend normalized by shipped packages.", "SUM(transport_cost_usd) / SUM(packages_shipped)", "fact_lane_movements", "transport_cost_usd, packages_shipped", "vw_weekly_network_kpis", "Week and region", "WEEKLY", "Compare cost efficiency across weeks and lanes.", "SELECT 1.0 * SUM(transport_cost_usd) / NULLIF(SUM(packages_shipped), 0) FROM fact_lane_movements;"),
    ("co2e_kg_per_package", "CO2e per Package", "STANDARD_KPI", "Estimated movement emissions normalized by shipped packages.", "SUM(distance_miles * trips_completed * emission_factor) / SUM(packages_shipped)", "fact_lane_movements, dim_lanes", "distance_miles, trips_completed, emission_factor_kg_co2e_per_mile, packages_shipped", "vw_weekly_network_kpis", "Week and region", "WEEKLY", "Compare emissions efficiency while controlling for volume.", "SELECT SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile) / NULLIF(SUM(m.packages_shipped), 0) FROM fact_lane_movements m JOIN dim_lanes l ON m.lane_id = l.lane_id;"),
    ("capacity_utilization", "Capacity Utilization", "STANDARD_KPI", "Processed node volume divided by available node capacity.", "SUM(packages_processed) / SUM(available_capacity_packages)", "fact_node_operations", "packages_processed, available_capacity_packages", "vw_weekly_node_performance", "Week and node", "WEEKLY", "Identify nodes approaching overload.", "SELECT 1.0 * SUM(packages_processed) / NULLIF(SUM(available_capacity_packages), 0) FROM fact_node_operations;"),
    ("volume_deviation_vs_plan", "Volume Deviation vs Plan", "STANDARD_KPI", "Difference between actual and planned volume as a share of planned volume.", "(SUM(actual) - SUM(planned)) / SUM(planned)", "fact_lane_movements, fact_node_operations", "packages_shipped, planned_packages, packages_processed, planned_volume", "vw_weekly_lane_performance", "Week and entity", "WEEKLY", "Identify demand or execution variance.", "SELECT 1.0 * (SUM(packages_shipped) - SUM(planned_packages)) / NULLIF(SUM(planned_packages), 0) FROM fact_lane_movements;"),
    ("exception_rate", "Exception Rate", "STANDARD_KPI", "Share of packages associated with a documented exception.", "SUM(exception_packages) / SUM(packages)", "fact_lane_movements, fact_node_operations", "exception_packages, packages_shipped, packages_processed", "vw_weekly_network_kpis", "Week and entity", "WEEKLY", "Quantify operational instability.", "SELECT 1.0 * SUM(exception_packages) / NULLIF(SUM(packages_shipped), 0) FROM fact_lane_movements;"),
    ("transit_delay_hours", "Transit Delay Hours", "STANDARD_KPI", "Package-weighted lane transit time above the lane plan.", "Weighted Actual Transit Hours - Planned Transit Hours", "fact_lane_movements, dim_lanes", "actual_transit_hours, packages_shipped, planned_transit_hours", "vw_weekly_lane_performance", "Week and lane", "WEEKLY", "Identify lane disruptions.", "SELECT SUM(actual_transit_hours * packages_shipped) / NULLIF(SUM(packages_shipped), 0) FROM fact_lane_movements;"),
    ("late_package_contribution_pct", "Late Package Contribution", "PLANNING_SIGNAL", "Entity late packages divided by network late packages.", "Entity Late Packages / Network Late Packages", "fact_lane_movements, fact_node_operations", "late_packages", "vw_weekly_lane_performance", "Week and entity", "WEEKLY", "Prioritize entities with the largest service impact.", "SELECT lane_id, SUM(late_packages) FROM fact_lane_movements GROUP BY lane_id;"),
    ("capacity_risk_level", "Capacity Risk Level", "PLANNING_SIGNAL", "Transparent rule classifying node overload risk.", "HIGH if utilization > 100%; MEDIUM if > 95%; otherwise LOW", "fact_node_operations", "packages_processed, available_capacity_packages", "vw_root_cause_signals", "Week and node", "WEEKLY", "Focus weekly capacity reviews.", "SELECT * FROM vw_root_cause_signals WHERE signal_code = 'NODE_CAPACITY_PRESSURE';"),
    ("projected_capacity_utilization", "Projected Capacity Utilization", "SCENARIO_OUTPUT", "Estimated node utilization after a lane volume reallocation.", "Projected Node Volume / Available Capacity", "vw_weekly_node_performance, scenario input", "packages_processed, available_capacity_packages, package_delta", "Python scenario module", "Scenario and node", "ON_DEMAND", "Warn about overload risk.", "Scenario calculation is intentionally separate from historical SQL views."),
]


def _daily_dates():
    return [START_DATE + timedelta(days=i) for i in range(12 * 7)]


def _lane_rows(rng: random.Random):
    latest_exception_start = LATEST_WEEK
    base_by_lane = {
        lane[0]: (3200 if lane[3] == "FC_TO_SC" else 1180)
        for lane in LANES
    }
    base_by_lane["SC_SEA_01__DS_BEL_01_EXP"] = 360
    for movement_date in _daily_dates():
        weekend = 0.82 if movement_date.weekday() >= 5 else 1.0
        for lane in LANES:
            lane_id, _, _, _, mode, _, planned_transit, _, vehicle_capacity, _, base_cost = lane
            planned = max(100, round(base_by_lane[lane_id] * weekend * rng.uniform(0.94, 1.06)))
            actual = max(0, round(planned * rng.uniform(0.96, 1.05)))
            transit = planned_transit * rng.uniform(0.92, 1.10)
            late_rate = rng.uniform(0.008, 0.022)
            exception_rate = rng.uniform(0.004, 0.014)
            if movement_date >= latest_exception_start and lane_id == "SC_SEA_01__DS_BEL_01":
                actual = round(planned * 1.28)
                transit = planned_transit + 2.1
                late_rate, exception_rate = 0.15, 0.065
            if movement_date >= latest_exception_start and lane_id == "SC_PDX_01__DS_SLM_01":
                transit = planned_transit + 2.6
                late_rate, exception_rate = 0.18, 0.075
            if movement_date >= latest_exception_start and lane_id == "SC_SEA_01__DS_BEL_01_EXP":
                transit = planned_transit + 0.35
                late_rate, exception_rate = 0.035, 0.018
            trips = max(1, math.ceil(actual / vehicle_capacity))
            trips_planned = max(1, math.ceil(planned / vehicle_capacity))
            cost_multiplier = 1.12 if movement_date >= latest_exception_start and mode == "EXPEDITED_GROUND" else 1.0
            cost = round(trips * base_cost * cost_multiplier, 2)
            yield (
                movement_date.isoformat(), lane_id, planned, actual, trips_planned, trips, cost,
                round(transit, 3), round(actual * late_rate), round(actual * exception_rate),
                actual if mode == "EXPEDITED_GROUND" else 0,
            )


def _node_rows(rng: random.Random):
    for operation_date in _daily_dates():
        weekend = 0.82 if operation_date.weekday() >= 5 else 1.0
        for node in NODES:
            node_id, _, node_type, _, _, _, _, _, capacity = node
            planned = round(capacity * weekend * (0.72 if node_type == "DS" else 0.68) * rng.uniform(0.94, 1.05))
            processed = round(planned * rng.uniform(0.97, 1.05))
            available_capacity = capacity
            late_rate, exception_rate = rng.uniform(0.008, 0.022), rng.uniform(0.005, 0.018)
            downtime = rng.uniform(0.0, 0.7)
            if operation_date >= LATEST_WEEK and node_id == "DS_BEL_01":
                processed = round(planned * 1.48)
                available_capacity = round(capacity * 0.86)
                late_rate, exception_rate, downtime = 0.14, 0.075, 2.2
            productivity = 18.0 if node_type == "DS" else 24.0
            labor_hours = processed / productivity * rng.uniform(0.96, 1.08)
            yield (
                operation_date.isoformat(), node_id, planned, processed, available_capacity,
                round(processed * late_rate), round(processed * exception_rate),
                round(labor_hours, 2), round(downtime, 2),
            )


def initialize_database(db_path: Path | str = DB_PATH, force: bool = False) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists() and not force:
        return db_path
    if db_path.exists():
        db_path.unlink()
    rng = random.Random(42)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany(
            "INSERT INTO dim_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '2026-01-01', NULL)",
            NODES,
        )
        conn.executemany(
            "INSERT INTO dim_lanes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
            LANES,
        )
        conn.executemany("INSERT INTO fact_lane_movements VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", _lane_rows(rng))
        conn.executemany("INSERT INTO fact_node_operations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", _node_rows(rng))
        conn.executemany("INSERT INTO metric_dictionary VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", METRICS)
        conn.executescript(VIEWS_SQL)
        conn.commit()
    finally:
        conn.close()
    return db_path


if __name__ == "__main__":
    print(initialize_database(force=True))
