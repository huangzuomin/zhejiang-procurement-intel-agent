#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TARGET = "~/.openclaw/workspace-zhejiang-procurement-intel-agent"
PACKAGING_STRATEGY = "agent_workspace_with_tool_layer"

TOOL_SCRIPTS = {
    "scripts/evaluate_scrape_quality.py",
    "scripts/prepare_deploy_dry_run.py",
    "scripts/query_opportunity_cards.py",
    "scripts/run_brief_from_db.py",
    "scripts/run_daily_pipeline.py",
    "scripts/run_health_report.py",
    "scripts/run_hourly_collection.py",
    "scripts/run_hourly_ingest.py",
    "scripts/validate.sh",
    "scripts/zfcg_browser_scraper.js",
}
ROOT_DEPLOYABLE_FILES = {
    "package.json",
}

FORBIDDEN_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "credentials",
    "secrets",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".log"}
FORBIDDEN_NAMES = {".env"}


def main() -> int:
    args = parse_args()
    payload = build_payload()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload)
    return 0 if not payload["forbidden_matches"] else 2


def build_payload() -> dict:
    deployable_files = sorted(_deployable_files())
    forbidden_matches = [path for path in deployable_files if _is_forbidden(path)]
    return {
        "runtime_target": RUNTIME_TARGET,
        "packaging_strategy": PACKAGING_STRATEGY,
        "recommended_scheme": "A",
        "deployable_files": deployable_files,
        "forbidden_matches": forbidden_matches,
        "entrypoints": {
            "hourly_collection": "python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db",
            "am_brief_from_db": "python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am",
            "record_am_push_success": "python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am --record-push-success",
            "pm_brief_from_db": "python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm",
            "health_report": "python3 scripts/run_health_report.py --today <date> --db-path data/procurement_intel.db --output reports/<date>/health_report.json",
            "controlled_backfill": "python3 scripts/run_hourly_ingest.py <snapshot.json> --today <date> --db-path data/procurement_intel.db --include-historical --run-type backfill --json",
            "brief_from_existing_json": "python3 scripts/run_daily_pipeline.py <zfcg-json> --today <date> --output-dir <output-dir>",
            "opportunity_cards_qa": "python3 scripts/query_opportunity_cards.py <opportunity_cards.json> '<question>'",
        },
    }


def _deployable_files() -> set[str]:
    files: set[str] = set()
    files.update(_files_under("openclaw/agent"))
    files.update(_files_under("src/procurement_intel"))
    for root_file in ROOT_DEPLOYABLE_FILES:
        if (ROOT / root_file).is_file():
            files.add(root_file)
    for script in TOOL_SCRIPTS:
        if (ROOT / script).is_file():
            files.add(script)
    return files


def _files_under(relative_dir: str) -> set[str]:
    base = ROOT / relative_dir
    if not base.exists():
        return set()
    return {
        path.relative_to(ROOT).as_posix()
        for path in base.rglob("*")
        if path.is_file() and not _is_forbidden(path.relative_to(ROOT).as_posix())
    }


def _is_forbidden(relative_path: str) -> bool:
    parts = set(Path(relative_path).parts)
    name = Path(relative_path).name
    suffix = Path(relative_path).suffix
    if parts & FORBIDDEN_PARTS:
        return True
    if name in FORBIDDEN_NAMES or name.startswith(".env."):
        return True
    return suffix in FORBIDDEN_SUFFIXES


def print_human(payload: dict) -> None:
    print(f"Runtime target: {payload['runtime_target']}")
    print(f"Packaging strategy: {payload['packaging_strategy']}")
    print(f"Recommended scheme: {payload['recommended_scheme']}")
    print(f"Deployable files: {len(payload['deployable_files'])}")
    for path in payload["deployable_files"]:
        print(f"- {path}")
    if payload["forbidden_matches"]:
        print("Forbidden matches:")
        for path in payload["forbidden_matches"]:
            print(f"- {path}")
    else:
        print("Forbidden matches: none")
    print("Entrypoints:")
    for name, command in payload["entrypoints"].items():
        print(f"- {name}: {command}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a deployment dry-run manifest without copying runtime files.")
    parser.add_argument("--json", action="store_true", help="Print JSON payload.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
