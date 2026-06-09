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
    assert "scripts/zfcg_browser_scraper.js" in payload["deployable_files"]
    assert "scripts/run_daily_pipeline.py" in payload["deployable_files"]
    assert "scripts/query_opportunity_cards.py" in payload["deployable_files"]
    assert "package.json" in payload["deployable_files"]
    assert payload["forbidden_matches"] == []
    assert all("node_modules" not in path for path in payload["deployable_files"])
    assert all("__pycache__" not in path for path in payload["deployable_files"])
