import sqlite3
import tempfile
import unittest
from pathlib import Path

from control_tower.database import LATEST_WEEK, initialize_database
from control_tower.queries import read_view
from control_tower.scenario import calculate_reallocation, calculate_reallocations


class ControlTowerBackendTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "control_tower.db"
        initialize_database(self.db_path, force=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_week_aggregation_starts_on_monday(self):
        network = read_view("vw_weekly_network_kpis", self.db_path)
        self.assertTrue(all(__import__("datetime").date.fromisoformat(value).weekday() == 0 for value in network["week_start"]))

    def test_seeded_exception_signals_exist(self):
        signals = read_view("vw_root_cause_signals", self.db_path)
        latest = signals[signals["week_start"] == LATEST_WEEK.isoformat()]
        codes = set(latest["signal_code"])
        self.assertIn("NODE_CAPACITY_PRESSURE", codes)
        self.assertIn("LANE_TRANSIT_DELAY", codes)
        self.assertIn("LANE_COST_LEAKAGE", codes)

    def test_carbon_kpi_matches_raw_calculation(self):
        conn = sqlite3.connect(self.db_path)
        try:
            expected = conn.execute("""
                SELECT SUM(l.distance_miles * m.trips_completed * l.emission_factor_kg_co2e_per_mile)
                     / SUM(m.packages_shipped)
                FROM fact_lane_movements m JOIN dim_lanes l ON m.lane_id = l.lane_id
                JOIN dim_nodes n ON l.origin_node_id = n.node_id
                WHERE m.movement_date BETWEEN '2026-05-18' AND '2026-05-24'
                  AND n.region = 'PACIFIC_NORTHWEST'
            """).fetchone()[0]
            actual = conn.execute("""
                SELECT co2e_kg_per_package FROM vw_weekly_network_kpis
                WHERE week_start = '2026-05-18' AND region = 'PACIFIC_NORTHWEST'
            """).fetchone()[0]
        finally:
            conn.close()
        self.assertAlmostEqual(expected, actual)

    def test_valid_reallocation_conserves_packages(self):
        lanes = read_view("vw_weekly_lane_performance", self.db_path)
        nodes = read_view("vw_weekly_node_performance", self.db_path)
        lanes = lanes[(lanes["week_start"] == LATEST_WEEK.isoformat()) & (lanes["lane_type"] == "SC_TO_DS")]
        nodes = nodes[(nodes["week_start"] == LATEST_WEEK.isoformat()) & (nodes["node_type"] == "DS")]
        result = calculate_reallocation(lanes, nodes, "SC_SEA_01__DS_BEL_01", "SC_SEA_01__DS_TAC_01", 1000)
        self.assertEqual(result.lane_comparison["projected_packages"].sum(), lanes["packages_shipped"].sum())

    def test_invalid_reallocation_is_rejected(self):
        lanes = read_view("vw_weekly_lane_performance", self.db_path)
        nodes = read_view("vw_weekly_node_performance", self.db_path)
        lanes = lanes[(lanes["week_start"] == LATEST_WEEK.isoformat()) & (lanes["lane_type"] == "SC_TO_DS")]
        nodes = nodes[(nodes["week_start"] == LATEST_WEEK.isoformat()) & (nodes["node_type"] == "DS")]
        with self.assertRaises(ValueError):
            calculate_reallocation(lanes, nodes, "SC_SEA_01__DS_BEL_01", "SC_SEA_01__DS_TAC_01", 999999)

    def test_multi_action_reallocation_conserves_packages(self):
        lanes = read_view("vw_weekly_lane_performance", self.db_path)
        nodes = read_view("vw_weekly_node_performance", self.db_path)
        lanes = lanes[(lanes["week_start"] == LATEST_WEEK.isoformat()) & (lanes["lane_type"] == "SC_TO_DS")]
        nodes = nodes[(nodes["week_start"] == LATEST_WEEK.isoformat()) & (nodes["node_type"] == "DS")]
        result = calculate_reallocations(
            lanes,
            nodes,
            [
                ("SC_SEA_01__DS_BEL_01", "SC_SEA_01__DS_TAC_01", 1000),
                ("SC_SEA_01__DS_BEL_01", "SC_SEA_01__DS_EVE_01", 500),
            ],
        )
        projected = result.lane_comparison.set_index("lane_id")["projected_packages"]
        baseline = lanes.set_index("lane_id")["packages_shipped"]
        self.assertEqual(projected.sum(), baseline.sum())
        self.assertEqual(projected["SC_SEA_01__DS_TAC_01"], baseline["SC_SEA_01__DS_TAC_01"] + 1000)
        self.assertEqual(projected["SC_SEA_01__DS_EVE_01"], baseline["SC_SEA_01__DS_EVE_01"] + 500)

    def test_unaffected_lane_costs_are_not_repriced(self):
        lanes = read_view("vw_weekly_lane_performance", self.db_path)
        nodes = read_view("vw_weekly_node_performance", self.db_path)
        lanes = lanes[(lanes["week_start"] == LATEST_WEEK.isoformat()) & (lanes["lane_type"] == "SC_TO_DS")]
        nodes = nodes[(nodes["week_start"] == LATEST_WEEK.isoformat()) & (nodes["node_type"] == "DS")]
        result = calculate_reallocations(
            lanes,
            nodes,
            [("SC_SEA_01__DS_BEL_01", "SC_SEA_01__DS_TAC_01", 1000)],
        )
        projected = result.lane_comparison.set_index("lane_id")
        unaffected_lane = projected.loc["SC_PDX_01__DS_PDX_01"]
        self.assertEqual(unaffected_lane["projected_cost_usd"], unaffected_lane["transport_cost_usd"])
        self.assertEqual(unaffected_lane["projected_co2e_kg"], unaffected_lane["co2e_kg"])


if __name__ == "__main__":
    unittest.main()
