import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_deploy_dry_run_reports_allowed_files_and_excludes_forbidden_patterns() -> None:
    result = subprocess.run(
        ["python3", "scripts/prepare_deploy_dry_run.py", "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["runtime_target"] == "~/.openclaw/workspace-zhejiang-procurement-intel-agent"
    assert payload["packaging_strategy"] == "agent_workspace_with_tool_layer"
    assert "openclaw/agent/AGENTS.md" in payload["deployable_files"]
    assert "src/procurement_intel/daily_pipeline.py" in payload["deployable_files"]
    assert "src/procurement_intel/storage.py" in payload["deployable_files"]
    assert "src/procurement_intel/hourly_ingestion.py" in payload["deployable_files"]
    assert "src/procurement_intel/db_briefing.py" in payload["deployable_files"]
    assert "src/procurement_intel/health.py" in payload["deployable_files"]
    assert "scripts/zfcg_browser_scraper.js" in payload["deployable_files"]
    assert "scripts/run_daily_pipeline.py" in payload["deployable_files"]
    assert "scripts/run_hourly_collection.py" in payload["deployable_files"]
    assert "scripts/run_hourly_ingest.py" in payload["deployable_files"]
    assert "scripts/run_brief_from_db.py" in payload["deployable_files"]
    assert "scripts/run_health_report.py" in payload["deployable_files"]
    assert "scripts/query_opportunity_cards.py" in payload["deployable_files"]
    assert "package.json" in payload["deployable_files"]
    assert "hourly_collection" in payload["entrypoints"]
    assert "am_brief_from_db" in payload["entrypoints"]
    assert "record_am_push_success" in payload["entrypoints"]
    assert "pm_brief_from_db" in payload["entrypoints"]
    assert "health_report" in payload["entrypoints"]
    assert "controlled_backfill" in payload["entrypoints"]
    assert payload["forbidden_matches"] == []
    assert all("node_modules" not in path for path in payload["deployable_files"])
    assert all("__pycache__" not in path for path in payload["deployable_files"])
