from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from control_tower.database import DB_PATH, initialize_database
from control_tower.queries import read_view, view_sql
from control_tower.scenario import calculate_reallocations

st.set_page_config(page_title="Weekly Transportation Network Control Tower", layout="wide")
initialize_database(DB_PATH)

OTD_TARGET = 0.97
EXCEPTION_RATE_TARGET = 0.03


@st.cache_data
def load_data():
    return {
        "network": read_view("vw_weekly_network_kpis"),
        "nodes": read_view("vw_weekly_node_performance"),
        "lanes": read_view("vw_weekly_lane_performance"),
        "signals": read_view("vw_root_cause_signals"),
        "metrics": read_view("vw_metric_dictionary"),
    }


def fmt_percent(value: float) -> str:
    return f"{value:.1%}"


def fmt_delta(value: float, kind: str = "number") -> str:
    return f"{value:+.1%}" if kind == "percent" else f"{value:+,.2f}"


def as_percent_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    display = frame.copy()
    for column in columns:
        display[column] = display[column] * 100
    return display


def percent_column_config(columns: list[str]) -> dict:
    return {
        column: st.column_config.NumberColumn(format="%.1f%%")
        for column in columns
    }


def build_region_scorecard(network: pd.DataFrame, week: str, region: str) -> pd.DataFrame:
    scorecard = region_filter(network, region)
    scorecard = scorecard[scorecard["week_start"] == week].copy()
    scorecard["otd_vs_target"] = scorecard["on_time_delivery_rate"] - OTD_TARGET
    scorecard["status"] = scorecard.apply(
        lambda row: "At Risk"
        if row["on_time_delivery_rate"] < OTD_TARGET or row["exception_rate"] > EXCEPTION_RATE_TARGET
        else "Healthy",
        axis=1,
    )
    for column in ["on_time_delivery_rate", "otd_vs_target", "exception_rate"]:
        scorecard[column] = scorecard[column] * 100
    return scorecard.rename(
        columns={
            "region": "Region",
            "status": "Status",
            "total_packages_shipped": "Packages",
            "on_time_delivery_rate": "OTD Rate",
            "otd_vs_target": "OTD vs Target",
            "cost_per_package_usd": "Cost / Package",
            "co2e_kg_per_package": "CO2e / Package",
            "exception_rate": "Exception Rate",
        }
    )[
        [
            "Region",
            "Status",
            "Packages",
            "OTD Rate",
            "OTD vs Target",
            "Cost / Package",
            "CO2e / Package",
            "Exception Rate",
        ]
    ].sort_values(["Status", "OTD Rate"], ascending=[False, True])


def build_action_queue(signals: pd.DataFrame, week: str, region: str, lanes: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    queue = signals[signals["week_start"] == week].copy()
    if region != "ALL":
        node_ids = set(nodes[nodes["region"] == region]["node_id"])
        lane_ids = set(lanes[lanes["region"] == region]["lane_id"])
        queue = queue[
            ((queue["entity_type"] == "NODE") & queue["entity_id"].isin(node_ids))
            | ((queue["entity_type"] == "LANE") & queue["entity_id"].isin(lane_ids))
        ]
    if queue.empty:
        return queue
    queue["severity_order"] = queue["severity"].map(severity_order).fillna(9)
    return queue.sort_values(["severity_order", "entity_id"]).rename(
        columns={
            "severity": "Priority",
            "entity_type": "Level",
            "entity_id": "Entity",
            "signal_name": "Signal",
            "business_message": "Why It Matters",
            "recommended_action": "Recommended Action",
        }
    )[["Priority", "Level", "Entity", "Signal", "Why It Matters", "Recommended Action"]]


def weekly_sidebar_filters(data):
    weeks = sorted(data["network"]["week_start"].unique(), reverse=True)
    regions = ["ALL"] + sorted(data["network"]["region"].unique())
    week = st.sidebar.selectbox("Planning week", weeks)
    region = st.sidebar.selectbox("Region", regions)
    return week, region


def region_filter(frame: pd.DataFrame, region: str) -> pd.DataFrame:
    return frame if region == "ALL" else frame[frame["region"] == region]


def page_overview(data, week, region):
    st.header("Executive Overview")
    st.caption("Weekly planning view for service, cost, capacity, and sustainability decisions.")
    current = region_filter(data["network"], region)
    selected = current[current["week_start"] == week]
    previous_week = sorted(current["week_start"].unique())
    prior = previous_week[previous_week.index(week) - 1] if week in previous_week and previous_week.index(week) > 0 else None
    previous = current[current["week_start"] == prior] if prior else pd.DataFrame()

    now = selected.sum(numeric_only=True)
    before = previous.sum(numeric_only=True) if not previous.empty else now
    now_otd = 1 - now["late_packages"] / now["total_packages_shipped"]
    before_otd = 1 - before["late_packages"] / before["total_packages_shipped"]
    now_cost = now["transport_cost_usd"] / now["total_packages_shipped"]
    before_cost = before["transport_cost_usd"] / before["total_packages_shipped"]
    now_co2 = now["co2e_kg"] / now["total_packages_shipped"]
    before_co2 = before["co2e_kg"] / before["total_packages_shipped"]
    now_exceptions = now["exception_packages"] / now["total_packages_shipped"]
    before_exceptions = before["exception_packages"] / before["total_packages_shipped"]
    node_week = region_filter(data["nodes"], region)
    node_week = node_week[node_week["week_start"] == week]
    max_utilization = node_week["capacity_utilization"].max()
    overloaded_nodes = int((node_week["capacity_utilization"] > 1.0).sum())

    cols = st.columns(4)
    cols[0].metric("Packages Shipped", f"{now['total_packages_shipped']:,.0f}", f"{now['total_packages_shipped'] - before['total_packages_shipped']:+,.0f}")
    cols[1].metric("On-Time Delivery", fmt_percent(now_otd), fmt_delta(now_otd - before_otd, "percent"))
    cols[2].metric("Cost per Package", f"${now_cost:.2f}", f"${now_cost - before_cost:+.2f}", delta_color="inverse")
    cols[3].metric("CO2e per Package", f"{now_co2:.3f} kg", f"{now_co2 - before_co2:+.3f} kg", delta_color="inverse")
    cols = st.columns(4)
    cols[0].metric("Late Packages", f"{now['late_packages']:,.0f}", f"{now['late_packages'] - before['late_packages']:+,.0f}", delta_color="inverse")
    cols[1].metric("Exception Rate", fmt_percent(now_exceptions), fmt_delta(now_exceptions - before_exceptions, "percent"), delta_color="inverse")
    cols[2].metric("Max Node Utilization", fmt_percent(max_utilization))
    signals = region_filter(data["signals"].merge(data["nodes"][["week_start", "node_id", "region"]].drop_duplicates(), left_on=["week_start", "entity_id"], right_on=["week_start", "node_id"], how="left"), region)
    cols[3].metric("Nodes Over Capacity", f"{overloaded_nodes:,}")

    trend = current.groupby("week_start", as_index=False).agg({"total_packages_shipped": "sum", "late_packages": "sum", "transport_cost_usd": "sum", "co2e_kg": "sum"})
    trend["on_time_delivery_rate"] = 1 - trend["late_packages"] / trend["total_packages_shipped"]
    trend["cost_per_package_usd"] = trend["transport_cost_usd"] / trend["total_packages_shipped"]
    left, right = st.columns(2)
    otd_chart = px.line(
        trend,
        x="week_start",
        y="on_time_delivery_rate",
        markers=True,
        title="On-Time Delivery Trend",
        labels={"week_start": "Week", "on_time_delivery_rate": "OTD Rate"},
    )
    otd_chart.update_yaxes(tickformat=".1%", range=[0.94, 1.0])
    otd_chart.add_hline(
        y=OTD_TARGET,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="97.0% target",
        annotation_position="bottom right",
    )
    otd_chart.add_vline(x=week, line_dash="dot", line_color="#64748b")
    left.plotly_chart(otd_chart, width="stretch")
    right.plotly_chart(px.line(trend, x="week_start", y="cost_per_package_usd", markers=True, title="Cost per Package Trend"), width="stretch")
    st.subheader("Regional Service Snapshot")
    st.caption("Use this scorecard to identify which regions need a planning review. Target OTD: 97.0%.")
    scorecard = build_region_scorecard(data["network"], week, region)
    st.dataframe(
        scorecard,
        width="stretch",
        hide_index=True,
        column_config={
            "Packages": st.column_config.NumberColumn(format="%,d"),
            "OTD Rate": st.column_config.ProgressColumn(format="%.1f%%", min_value=0.0, max_value=100.0),
            "OTD vs Target": st.column_config.NumberColumn(format="%+.1f%%"),
            "Cost / Package": st.column_config.NumberColumn(format="$%.2f"),
            "CO2e / Package": st.column_config.NumberColumn(format="%.3f kg"),
            "Exception Rate": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.subheader("Weekly Action Queue")
    st.caption("Rule-based signals are prioritized for manager review. Detailed definitions remain available in Data & Metric Catalog.")
    action_queue = build_action_queue(data["signals"], week, region, data["lanes"], data["nodes"])
    if action_queue.empty:
        st.success("No planning signals were triggered for the selected week.")
    else:
        st.dataframe(action_queue, width="stretch", hide_index=True)


def page_deep_dive(data, week, region):
    st.header("Root Cause Deep Dive")
    st.caption("Planning signals are transparent business rules used to prioritize investigation.")
    nodes = region_filter(data["nodes"], region)
    lanes = region_filter(data["lanes"], region)
    node_week = nodes[nodes["week_start"] == week].copy()
    lane_week = lanes[lanes["week_start"] == week].copy()
    total_late = max(lane_week["late_packages"].sum(), 1)
    lane_week["late_package_contribution"] = lane_week["late_packages"] / total_late
    lane_rank = lane_week.sort_values("late_packages", ascending=False)
    left, right = st.columns(2)
    left.plotly_chart(px.bar(lane_rank, x="lane_id", y="late_packages", title="Late Package Pareto by Lane"), width="stretch")
    utilization_chart = px.bar(node_week.sort_values("capacity_utilization", ascending=False), x="node_id", y="capacity_utilization", color="capacity_utilization", title="Node Capacity Utilization")
    utilization_chart.update_yaxes(tickformat=".0%")
    right.plotly_chart(utilization_chart, width="stretch")
    st.subheader("Lane Contribution Analysis")
    lane_display = lane_rank[["lane_id", "packages_shipped", "late_packages", "late_package_contribution", "transit_delay_hours", "cost_per_package_usd", "co2e_kg_per_package"]].rename(
        columns={
            "lane_id": "Lane",
            "packages_shipped": "Packages",
            "late_packages": "Late Packages",
            "late_package_contribution": "Late Package Contribution",
            "transit_delay_hours": "Transit Delay Hours",
            "cost_per_package_usd": "Cost / Package",
            "co2e_kg_per_package": "CO2e / Package",
        }
    )
    lane_display = as_percent_columns(lane_display, ["Late Package Contribution"])
    st.dataframe(
        lane_display,
        width="stretch",
        hide_index=True,
        column_config={
            **percent_column_config(["Late Package Contribution"]),
            "Packages": st.column_config.NumberColumn(format="%,d"),
            "Late Packages": st.column_config.NumberColumn(format="%,d"),
            "Cost / Package": st.column_config.NumberColumn(format="$%.2f"),
            "CO2e / Package": st.column_config.NumberColumn(format="%.3f kg"),
        },
    )
    st.subheader("Node Performance")
    node_display = node_week[["node_id", "planned_volume", "packages_processed", "capacity_utilization", "volume_deviation_vs_plan", "exception_rate", "downtime_hours"]].sort_values("capacity_utilization", ascending=False).rename(
        columns={
            "node_id": "Node",
            "planned_volume": "Planned Volume",
            "packages_processed": "Processed Packages",
            "capacity_utilization": "Capacity Utilization",
            "volume_deviation_vs_plan": "Volume Deviation vs Plan",
            "exception_rate": "Exception Rate",
            "downtime_hours": "Downtime Hours",
        }
    )
    node_percentage_columns = ["Capacity Utilization", "Volume Deviation vs Plan", "Exception Rate"]
    node_display = as_percent_columns(node_display, node_percentage_columns)
    st.dataframe(
        node_display,
        width="stretch",
        hide_index=True,
        column_config=percent_column_config(node_percentage_columns),
    )
    st.subheader("Management Summary")
    signals = data["signals"][data["signals"]["week_start"] == week]
    if region != "ALL":
        node_ids = set(nodes["node_id"])
        lane_ids = set(lanes["lane_id"])
        signals = signals[
            ((signals["entity_type"] == "NODE") & signals["entity_id"].isin(node_ids))
            | ((signals["entity_type"] == "LANE") & signals["entity_id"].isin(lane_ids))
        ]
    if signals.empty:
        st.success("No rule-based planning signals were triggered for the selected week.")
    else:
        for _, signal in signals.sort_values("severity").iterrows():
            st.write(f"**{signal['severity']} | {signal['entity_id']} | {signal['signal_name']}**: {signal['business_message']} {signal['recommended_action']}")


def page_scenario(data, week, region):
    st.header("Scenario Planner")
    st.caption(
        "Projected results are planning estimates for SC_TO_DS lanes only. "
        "They remain separate from network-level historical KPIs."
    )
    lanes = region_filter(data["lanes"], region)
    nodes = region_filter(data["nodes"], region)
    lanes = lanes[(lanes["week_start"] == week) & (lanes["lane_type"] == "SC_TO_DS")].copy()
    nodes = nodes[(nodes["week_start"] == week) & (nodes["node_type"] == "DS")].copy()
    options = sorted(lanes["lane_id"])
    source = st.selectbox("Source lane", options, index=options.index("SC_SEA_01__DS_BEL_01") if "SC_SEA_01__DS_BEL_01" in options else 0)
    source_region = lanes.loc[lanes["lane_id"] == source, "region"].iloc[0]
    destination_options = sorted(
        lanes.loc[(lanes["region"] == source_region) & (lanes["lane_id"] != source), "lane_id"]
    )
    preferred_destination = "SC_SEA_01__DS_TAC_01"
    destination = st.selectbox(
        "Action 1 destination lane",
        destination_options,
        index=destination_options.index(preferred_destination) if preferred_destination in destination_options else 0,
    )
    max_packages = int(lanes.loc[lanes["lane_id"] == source, "packages_shipped"].iloc[0])
    packages = st.number_input("Action 1 packages to reallocate", min_value=1, max_value=max_packages, value=min(1000, max_packages), step=100)
    actions = [(source, destination, int(packages))]
    add_second_action = st.checkbox("Add a second reallocation action")
    if add_second_action:
        second_destination_options = [lane for lane in destination_options if lane != destination]
        preferred_second_destination = "SC_SEA_01__DS_EVE_01"
        second_destination = st.selectbox(
            "Action 2 destination lane",
            second_destination_options,
            index=second_destination_options.index(preferred_second_destination)
            if preferred_second_destination in second_destination_options
            else 0,
        )
        remaining_packages = max_packages - int(packages)
        second_packages = st.number_input(
            "Action 2 packages to reallocate",
            min_value=1,
            max_value=max(1, remaining_packages),
            value=min(1000, max(1, remaining_packages)),
            step=100,
        )
        actions.append((source, second_destination, int(second_packages)))
    with st.expander("Optional Action 1 overrides"):
        capacity_override = st.number_input("Destination weekly capacity override (0 = use baseline)", min_value=0, value=0, step=100)
        cost_override = st.number_input("Destination cost per trip override (0 = use baseline)", min_value=0.0, value=0.0, step=10.0)
        delay_override = st.number_input("Additional destination transit delay hours", min_value=0.0, value=0.0, step=0.5)
    try:
        result = calculate_reallocations(
            lanes,
            nodes,
            actions,
            {destination: int(capacity_override)} if capacity_override else None,
            {destination: float(cost_override)} if cost_override else None,
            {destination: float(delay_override)} if delay_override else None,
        )
    except ValueError as exc:
        st.error(str(exc))
        return
    st.info(result.summary)
    for warning in result.warnings:
        st.warning(warning)
    comparison = result.kpi_comparison.copy()
    st.subheader("Baseline vs Proposed")
    scenario_metrics = comparison.set_index("metric")
    cards = st.columns(4)
    cards[0].metric(
        "Packages Conserved",
        f"{scenario_metrics.loc['Total Packages', 'proposed']:,.0f}",
        f"{scenario_metrics.loc['Total Packages', 'change']:+,.0f}",
    )
    cards[1].metric(
        "Transportation Cost",
        f"${scenario_metrics.loc['Transportation Cost', 'proposed']:,.0f}",
        f"${scenario_metrics.loc['Transportation Cost', 'change']:,.0f}",
        delta_color="inverse",
    )
    cards[2].metric(
        "Estimated OTD",
        fmt_percent(scenario_metrics.loc["Estimated OTD Rate", "proposed"]),
        fmt_delta(scenario_metrics.loc["Estimated OTD Rate", "change"], "percent"),
    )
    cards[3].metric(
        "CO2e",
        f"{scenario_metrics.loc['CO2e (kg)', 'proposed']:,.0f} kg",
        f"{scenario_metrics.loc['CO2e (kg)', 'change']:+,.0f} kg",
        delta_color="inverse",
    )
    st.caption("CO2e is retained as a secondary trade-off metric because network planning decisions can change vehicle trips and distance traveled.")
    comparison_display = comparison.copy()
    percentage_rows = comparison_display["metric"] == "Estimated OTD Rate"
    comparison_display.loc[percentage_rows, ["baseline", "proposed", "change"]] = (
        comparison_display.loc[percentage_rows, ["baseline", "proposed", "change"]] * 100
    )
    comparison_display["baseline"] = comparison_display.apply(
        lambda row: f"{row['baseline']:.1f}%" if row["metric"] == "Estimated OTD Rate" else f"{row['baseline']:,.2f}",
        axis=1,
    )
    comparison_display["proposed"] = comparison_display.apply(
        lambda row: f"{row['proposed']:.1f}%" if row["metric"] == "Estimated OTD Rate" else f"{row['proposed']:,.2f}",
        axis=1,
    )
    comparison_display["change"] = comparison_display.apply(
        lambda row: f"{row['change']:+.1f} pts" if row["metric"] == "Estimated OTD Rate" else f"{row['change']:+,.2f}",
        axis=1,
    )
    st.dataframe(comparison_display, width="stretch", hide_index=True)
    left, right = st.columns(2)
    cost_chart = px.bar(
        pd.DataFrame(
            {
                "Plan": ["Baseline", "Proposed"],
                "Transportation Cost": [
                    scenario_metrics.loc["Transportation Cost", "baseline"],
                    scenario_metrics.loc["Transportation Cost", "proposed"],
                ],
            }
        ),
        x="Plan",
        y="Transportation Cost",
        color="Plan",
        title="Transportation Cost Impact",
    )
    cost_chart.update_yaxes(tickprefix="$", tickformat=",")
    left.plotly_chart(cost_chart, width="stretch")
    service_chart = px.bar(
        pd.DataFrame(
            {
                "Plan": ["Baseline", "Proposed"],
                "Estimated OTD Rate": [
                    scenario_metrics.loc["Estimated OTD Rate", "baseline"],
                    scenario_metrics.loc["Estimated OTD Rate", "proposed"],
                ],
            }
        ),
        x="Plan",
        y="Estimated OTD Rate",
        color="Plan",
        title="Estimated Service Impact",
    )
    service_chart.update_yaxes(tickformat=".1%", range=[0.90, 1.0])
    service_chart.add_hline(
        y=OTD_TARGET,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="97.0% target",
        annotation_position="bottom right",
    )
    right.plotly_chart(service_chart, width="stretch")
    st.subheader("Projected Node Capacity")
    st.caption(
        "Projected node capacity shows how the lane reallocation changes weekly delivery-station workload. "
        "Projected utilization equals projected packages divided by available weekly processing capacity. "
        "Values above 100% require a mitigation plan."
    )
    projected_nodes = result.node_comparison[["node_id", "packages_processed", "projected_packages", "available_capacity_packages", "capacity_utilization", "projected_capacity_utilization"]].rename(
        columns={
            "node_id": "Node",
            "packages_processed": "Baseline Packages",
            "projected_packages": "Projected Packages",
            "available_capacity_packages": "Available Capacity",
            "capacity_utilization": "Baseline Utilization",
            "projected_capacity_utilization": "Projected Utilization",
        }
    )
    projected_nodes["Package Change"] = projected_nodes["Projected Packages"] - projected_nodes["Baseline Packages"]
    utilization_columns = ["Baseline Utilization", "Projected Utilization"]
    projected_nodes = as_percent_columns(projected_nodes, utilization_columns)
    projected_nodes["Capacity Status"] = projected_nodes["Projected Utilization"].apply(
        lambda value: "Over Capacity" if value > 100 else "Within Capacity"
    )
    projected_nodes = projected_nodes[
        [
            "Node",
            "Baseline Packages",
            "Package Change",
            "Projected Packages",
            "Available Capacity",
            "Baseline Utilization",
            "Projected Utilization",
            "Capacity Status",
        ]
    ]
    st.dataframe(
        projected_nodes,
        width="stretch",
        hide_index=True,
        column_config={
            **percent_column_config(utilization_columns),
            "Package Change": st.column_config.NumberColumn(format="%+d"),
        },
    )
    overloaded_nodes = projected_nodes[projected_nodes["Projected Utilization"] > 100]
    st.subheader("Residual Risk")
    if overloaded_nodes.empty:
        st.success("The proposed plan keeps every delivery station within available weekly capacity.")
    else:
        for _, row in overloaded_nodes.iterrows():
            residual_packages = row["Projected Packages"] - row["Available Capacity"]
            st.warning(
                f"{row['Node']} remains {row['Projected Utilization'] - 100:.1f} percentage points above capacity "
                f"after reallocation. Additional mitigation required: {residual_packages:,.0f} packages."
            )
    st.subheader("Projected Lane Flow")
    projected_lanes = result.lane_comparison.copy()
    projected_lanes["Package Change"] = projected_lanes["projected_packages"] - projected_lanes["packages_shipped"]
    projected_lanes["Trip Change"] = projected_lanes["projected_trips"] - projected_lanes["trips_completed"]
    projected_lanes["Cost Change"] = projected_lanes["projected_cost_usd"] - projected_lanes["transport_cost_usd"]
    projected_lanes["CO2e Change"] = projected_lanes["projected_co2e_kg"] - projected_lanes["co2e_kg"]
    affected_lanes = projected_lanes[projected_lanes["Package Change"] != 0].rename(
        columns={
            "lane_id": "Lane",
            "packages_shipped": "Baseline Packages",
            "projected_packages": "Projected Packages",
            "trips_completed": "Baseline Trips",
            "projected_trips": "Projected Trips",
        }
    )
    lane_columns = [
        "Lane",
        "Baseline Packages",
        "Package Change",
        "Projected Packages",
        "Baseline Trips",
        "Trip Change",
        "Projected Trips",
        "Cost Change",
        "CO2e Change",
    ]
    st.caption("Only lanes changed by the proposed reallocation plan are shown by default.")
    st.dataframe(
        affected_lanes[lane_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "Package Change": st.column_config.NumberColumn(format="%+d"),
            "Trip Change": st.column_config.NumberColumn(format="%+d"),
            "Cost Change": st.column_config.NumberColumn(format="$%+.0f"),
            "CO2e Change": st.column_config.NumberColumn(format="%+.0f kg"),
        },
    )
    with st.expander("View all SC_TO_DS lane projections"):
        st.dataframe(
            projected_lanes[
                [
                    "lane_id",
                    "packages_shipped",
                    "projected_packages",
                    "trips_completed",
                    "projected_trips",
                    "transport_cost_usd",
                    "projected_cost_usd",
                ]
            ],
            width="stretch",
            hide_index=True,
        )


def page_catalog(data, classification):
    st.header("Data & Metric Catalog")
    st.caption("Metric definitions, SQL lineage, and decision use cases.")
    metrics = data["metrics"]
    if classification != "ALL":
        metrics = metrics[metrics["metric_classification"] == classification]
    search = st.text_input("Search metrics")
    if search:
        metrics = metrics[metrics.astype(str).apply(lambda col: col.str.contains(search, case=False)).any(axis=1)]
    st.dataframe(metrics[["metric_name", "metric_classification", "business_definition", "formula_display", "sql_view_name", "data_grain", "refresh_cadence", "decision_use_case"]], width="stretch", hide_index=True)
    if metrics.empty:
        return
    metric = st.selectbox("Inspect metric SQL", metrics["metric_name"])
    row = metrics[metrics["metric_name"] == metric].iloc[0]
    st.write(f"**Source tables:** {row['source_tables']}")
    st.write(f"**Source columns:** {row['source_columns']}")
    st.code(row["representative_sql"], language="sql")
    with st.expander("Inspect full SQL view definition"):
        st.code(view_sql(row["sql_view_name"]) or "Calculated in the Python scenario module.", language="sql")


data = load_data()
st.sidebar.title("Weekly Transportation Network Control Tower")
page = st.sidebar.radio("Page", ["Executive Overview", "Root Cause Deep Dive", "Scenario Planner", "Data & Metric Catalog"])
if page == "Executive Overview":
    week, region = weekly_sidebar_filters(data)
    page_overview(data, week, region)
elif page == "Root Cause Deep Dive":
    week, region = weekly_sidebar_filters(data)
    page_deep_dive(data, week, region)
elif page == "Scenario Planner":
    week, region = weekly_sidebar_filters(data)
    page_scenario(data, week, region)
else:
    classifications = ["ALL"] + sorted(data["metrics"]["metric_classification"].unique())
    classification = st.sidebar.selectbox("Metric classification", classifications)
    page_catalog(data, classification)

