from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .database import DB_PATH, initialize_database


def connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    initialize_database(db_path)
    return sqlite3.connect(db_path)


def read_view(view_name: str, db_path: Path | str = DB_PATH) -> pd.DataFrame:
    allowed = {
        "vw_weekly_network_kpis",
        "vw_weekly_node_performance",
        "vw_weekly_lane_performance",
        "vw_root_cause_signals",
        "vw_metric_dictionary",
    }
    if view_name not in allowed:
        raise ValueError(f"Unsupported view: {view_name}")
    conn = connection(db_path)
    try:
        return pd.read_sql_query(f"SELECT * FROM {view_name}", conn)
    finally:
        conn.close()


def view_sql(view_name: str, db_path: Path | str = DB_PATH) -> str:
    conn = connection(db_path)
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = ?", (view_name,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else ""
