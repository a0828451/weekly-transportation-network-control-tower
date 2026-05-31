from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ScenarioResult:
    lane_comparison: pd.DataFrame
    node_comparison: pd.DataFrame
    kpi_comparison: pd.DataFrame
    warnings: list[str]
    summary: str


def _totals(lanes: pd.DataFrame) -> dict[str, float]:
    packages = float(lanes["projected_packages"].sum())
    late = float((lanes["projected_packages"] * lanes["projected_late_rate"]).sum())
    return {
        "Total Packages": packages,
        "Transportation Cost": float(lanes["projected_cost_usd"].sum()),
        "CO2e (kg)": float(lanes["projected_co2e_kg"].sum()),
        "Estimated OTD Rate": 1.0 - late / packages if packages else 0.0,
    }


def calculate_reallocation(
    lanes: pd.DataFrame,
    nodes: pd.DataFrame,
    source_lane: str,
    destination_lane: str,
    packages_to_move: int,
    destination_capacity_override: int | None = None,
    destination_cost_per_trip_override: float | None = None,
    destination_delay_override: float | None = None,
) -> ScenarioResult:
    return calculate_reallocations(
        lanes,
        nodes,
        [(source_lane, destination_lane, packages_to_move)],
        {destination_lane: destination_capacity_override} if destination_capacity_override is not None else None,
        {destination_lane: destination_cost_per_trip_override} if destination_cost_per_trip_override is not None else None,
        {destination_lane: destination_delay_override} if destination_delay_override is not None else None,
    )


def calculate_reallocations(
    lanes: pd.DataFrame,
    nodes: pd.DataFrame,
    actions: list[tuple[str, str, int]],
    destination_capacity_overrides: dict[str, int] | None = None,
    destination_cost_per_trip_overrides: dict[str, float] | None = None,
    destination_delay_overrides: dict[str, float] | None = None,
) -> ScenarioResult:
    if not actions:
        raise ValueError("Add at least one reallocation action.")
    lane_df = lanes.copy()
    lane_df = lane_df.set_index("lane_id", drop=False)
    lane_df["projected_packages"] = lane_df["packages_shipped"].astype(float)
    node_df = nodes.copy().set_index("node_id", drop=False)
    node_df["projected_packages"] = node_df["packages_processed"].astype(float)
    action_summaries = []
    affected_lanes = set()
    for source_lane, destination_lane, packages_to_move in actions:
        if packages_to_move <= 0:
            raise ValueError("Packages to move must be greater than zero.")
        if source_lane == destination_lane:
            raise ValueError("Source and destination lanes must be different.")
        if source_lane not in lane_df.index or destination_lane not in lane_df.index:
            raise ValueError("Source and destination lanes must exist in the selected week.")
        source, destination = lane_df.loc[source_lane], lane_df.loc[destination_lane]
        if source["region"] != destination["region"]:
            raise ValueError("Source and destination lanes must belong to the same planning region.")
        if packages_to_move > lane_df.loc[source_lane, "projected_packages"]:
            raise ValueError("Combined reallocated packages cannot exceed the source lane volume.")
        lane_df.loc[source_lane, "projected_packages"] -= packages_to_move
        lane_df.loc[destination_lane, "projected_packages"] += packages_to_move
        affected_lanes.update([source_lane, destination_lane])
        if source["destination_node_id"] in node_df.index:
            node_df.loc[source["destination_node_id"], "projected_packages"] -= packages_to_move
        if destination["destination_node_id"] in node_df.index:
            node_df.loc[destination["destination_node_id"], "projected_packages"] += packages_to_move
        action_summaries.append(f"{packages_to_move:,} packages from {source_lane} to {destination_lane}")

    lane_df["projected_trips"] = lane_df["trips_completed"]
    lane_df["projected_cost_usd"] = lane_df["transport_cost_usd"]
    lane_df["projected_co2e_kg"] = lane_df["co2e_kg"]
    for lane_id in affected_lanes:
        projected_packages = lane_df.loc[lane_id, "projected_packages"]
        projected_trips = (
            math.ceil(projected_packages / lane_df.loc[lane_id, "vehicle_capacity_packages"])
            if projected_packages > 0
            else 0
        )
        lane_df.loc[lane_id, "projected_trips"] = projected_trips
        lane_df.loc[lane_id, "projected_cost_usd"] = projected_trips * lane_df.loc[lane_id, "base_cost_usd_per_trip"]
        lane_df.loc[lane_id, "projected_co2e_kg"] = (
            projected_trips
            * lane_df.loc[lane_id, "distance_miles"]
            * lane_df.loc[lane_id, "emission_factor_kg_co2e_per_mile"]
        )
    lane_df["projected_late_rate"] = 1.0 - lane_df["on_time_delivery_rate"]
    for destination_lane, override in (destination_cost_per_trip_overrides or {}).items():
        lane_df.loc[destination_lane, "projected_cost_usd"] = lane_df.loc[destination_lane, "projected_trips"] * override
    for destination_lane, override in (destination_delay_overrides or {}).items():
        # Transparent service estimate: each additional delay hour adds two percentage points of late risk.
        lane_df.loc[destination_lane, "projected_late_rate"] = min(
            0.95, max(0.0, lane_df.loc[destination_lane, "projected_late_rate"] + 0.02 * override)
        )
    for destination_lane, override in (destination_capacity_overrides or {}).items():
        destination_node = lane_df.loc[destination_lane, "destination_node_id"]
        if destination_node in node_df.index:
            node_df.loc[destination_node, "available_capacity_packages"] = override
    node_df["projected_capacity_utilization"] = (
        node_df["projected_packages"] / node_df["available_capacity_packages"]
    )

    baseline_df = lane_df.copy()
    baseline_df["projected_packages"] = baseline_df["packages_shipped"]
    baseline_df["projected_cost_usd"] = baseline_df["transport_cost_usd"]
    baseline_df["projected_co2e_kg"] = baseline_df["co2e_kg"]
    baseline_df["projected_late_rate"] = 1.0 - baseline_df["on_time_delivery_rate"]
    baseline, proposed = _totals(baseline_df), _totals(lane_df)
    kpis = pd.DataFrame(
        [{"metric": metric, "baseline": baseline[metric], "proposed": proposed[metric], "change": proposed[metric] - baseline[metric]}
         for metric in baseline]
    )
    warnings = []
    overloaded = node_df[node_df["projected_capacity_utilization"] > 1.0]
    for _, row in overloaded.iterrows():
        warnings.append(f"{row['node_id']} is projected above capacity at {row['projected_capacity_utilization']:.1%}.")
    if abs(lane_df["projected_packages"].sum() - lanes["packages_shipped"].sum()) > 0.001:
        raise ValueError("Scenario package conservation check failed.")
    summary = (
        f"Apply {len(actions)} reallocation action(s): {'; '.join(action_summaries)}. "
        f"Projected transportation cost changes by ${proposed['Transportation Cost'] - baseline['Transportation Cost']:,.0f}, "
        f"and estimated OTD changes by {proposed['Estimated OTD Rate'] - baseline['Estimated OTD Rate']:+.2%}."
    )
    return ScenarioResult(
        lane_df.reset_index(drop=True), node_df.reset_index(drop=True), kpis, warnings, summary
    )
