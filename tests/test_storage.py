import sqlite3

from procurement_intel.storage import SQLiteStore


def test_initializes_required_tables(tmp_path):
    db_path = tmp_path / "procurement_intel.db"

    store = SQLiteStore(db_path)
    store.initialize()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("select name from sqlite_master where type = 'table'")
        }

    assert {
        "fetch_runs",
        "notices",
        "notice_details",
        "opportunity_cards",
        "push_events",
        "quality_reports",
    }.issubset(tables)
