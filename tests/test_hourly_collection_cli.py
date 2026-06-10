import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hourly_collection_dry_run_prints_scraper_and_ingest_commands(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    result = subprocess.run(
        [
            "python3",
            "scripts/run_hourly_collection.py",
            "--today",
            "2026-06-10",
            "--hour",
            "10",
            "--db-path",
            str(db_path),
            "--dry-run",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["mode"] == "hourly"
    assert payload["today"] == "2026-06-10"
    assert payload["hour"] == "10"
    assert "zfcg_browser_scraper.js" in payload["scraper_command"][1]
    assert "--known-urls-file" in payload["scraper_command"]
    assert "run_hourly_ingest.py" in payload["ingest_command"][1]
    assert payload["snapshot_path"].endswith("data/snapshots/2026-06-10/10.json")
    assert payload["known_urls_path"].endswith("data/runtime/2026-06-10/known_urls.txt")


def test_hourly_collection_dry_run_writes_known_urls_file(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    known_dir = tmp_path / "runtime"

    result = subprocess.run(
        [
            "python3",
            "scripts/run_hourly_collection.py",
            "--today",
            "2026-06-10",
            "--hour",
            "11",
            "--db-path",
            str(db_path),
            "--runtime-dir",
            str(known_dir),
            "--dry-run",
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert Path(payload["known_urls_path"]).exists()
