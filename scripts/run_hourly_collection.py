#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from procurement_intel.storage import SQLiteStore


def main() -> int:
    args = parse_args()
    today = args.today
    hour = normalize_hour(args.hour)
    db_path = Path(args.db_path)
    runtime_dir = Path(args.runtime_dir) / today
    snapshot_dir = Path(args.snapshot_dir) / today
    known_urls_path = runtime_dir / "known_urls.txt"
    snapshot_path = snapshot_dir / f"{hour}.json"

    store = SQLiteStore(db_path)
    store.initialize()
    known_count = write_known_urls(store, today=today, output_path=known_urls_path)

    scraper_command = build_scraper_command(
        today=today,
        limit=args.limit,
        detail_limit=args.detail_limit,
        known_urls_path=known_urls_path,
        snapshot_path=snapshot_path,
        timeout_ms=args.timeout_ms,
        render_wait_ms=args.render_wait_ms,
        delay_ms=args.delay_ms,
    )
    ingest_command = build_ingest_command(
        today=today,
        db_path=db_path,
        snapshot_path=snapshot_path,
    )
    payload = {
        "mode": "hourly",
        "today": today,
        "hour": hour,
        "db_path": str(db_path),
        "known_urls_path": str(known_urls_path),
        "known_url_count": known_count,
        "snapshot_path": str(snapshot_path),
        "scraper_command": scraper_command,
        "ingest_command": ingest_command,
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        print_output(payload, as_json=args.json)
        return 0

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now().isoformat(timespec="seconds")
    scraper = subprocess.run(scraper_command, cwd=ROOT, capture_output=True, text=True)
    payload["scraper_returncode"] = scraper.returncode
    if scraper.returncode != 0:
        record_failed_run(
            store,
            today=today,
            hour=hour,
            started_at=started_at,
            error=scraper.stderr.strip() or scraper.stdout.strip() or "scraper failed",
        )
        payload["error"] = "scraper_failed"
        payload["stderr"] = scraper.stderr
        print_output(payload, as_json=args.json)
        return scraper.returncode or 1

    ingest = subprocess.run(ingest_command, cwd=ROOT, capture_output=True, text=True)
    payload["ingest_returncode"] = ingest.returncode
    if ingest.stdout.strip():
        payload["ingest_stdout"] = parse_json_or_text(ingest.stdout)
    if ingest.stderr.strip():
        payload["ingest_stderr"] = ingest.stderr
    if ingest.returncode != 0:
        payload["error"] = "ingest_failed"
        print_output(payload, as_json=args.json)
        return ingest.returncode or 1

    print_output(payload, as_json=args.json)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one hourly Zhejiang procurement collection into SQLite.")
    parser.add_argument("--today", required=True, help="Collection date in YYYY-MM-DD.")
    parser.add_argument("--hour", required=True, help="Collection hour, e.g. 09 or 15.")
    parser.add_argument("--db-path", default="data/procurement_intel.db", help="SQLite database path.")
    parser.add_argument("--runtime-dir", default="data/runtime", help="Directory for runtime helper files.")
    parser.add_argument("--snapshot-dir", default="data/snapshots", help="Directory for raw scraper snapshots.")
    parser.add_argument("--limit", type=int, default=300, help="Per-column list collection limit.")
    parser.add_argument("--detail-limit", type=int, default=300, help="Per-column detail enrichment limit.")
    parser.add_argument("--timeout-ms", type=int, default=45000, help="Browser/detail request timeout.")
    parser.add_argument("--render-wait-ms", type=int, default=5000, help="Initial page render wait.")
    parser.add_argument("--delay-ms", type=int, default=800, help="Delay between detail requests.")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without launching the browser.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    return parser.parse_args()


def normalize_hour(value: str) -> str:
    try:
        return f"{int(value):02d}"
    except ValueError:
        return value


def write_known_urls(store: SQLiteStore, *, today: str, output_path: Path) -> int:
    urls = sorted(store.known_urls_for_date(today))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")
    return len(urls)


def build_scraper_command(
    *,
    today: str,
    limit: int,
    detail_limit: int,
    known_urls_path: Path,
    snapshot_path: Path,
    timeout_ms: int,
    render_wait_ms: int,
    delay_ms: int,
) -> list[str]:
    return [
        "node",
        "scripts/zfcg_browser_scraper.js",
        "--targets",
        "intention,bid",
        "--limit",
        str(limit),
        "--detail-limit",
        str(detail_limit),
        "--known-urls-file",
        str(known_urls_path),
        "--output",
        str(snapshot_path),
        "--timeout-ms",
        str(timeout_ms),
        "--render-wait-ms",
        str(render_wait_ms),
        "--delay-ms",
        str(delay_ms),
    ]


def build_ingest_command(*, today: str, db_path: Path, snapshot_path: Path) -> list[str]:
    return [
        "python3",
        "scripts/run_hourly_ingest.py",
        str(snapshot_path),
        "--today",
        today,
        "--db-path",
        str(db_path),
        "--run-type",
        "hourly",
        "--json",
    ]


def record_failed_run(
    store: SQLiteStore,
    *,
    today: str,
    hour: str,
    started_at: str,
    error: str,
) -> None:
    finished_at = datetime.now().isoformat(timespec="seconds")
    store.record_fetch_run(
        run_id=f"hourly-{today}-{hour}-failed",
        run_type="hourly",
        started_at=started_at,
        finished_at=finished_at,
        source="zfcg_browser_scraper",
        raw_count=0,
        new_count=0,
        enriched_count=0,
        status="failed",
        error=error[:1000],
    )


def parse_json_or_text(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value.strip()


def print_output(payload: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"mode: {payload['mode']}")
    print(f"today: {payload['today']}")
    print(f"hour: {payload['hour']}")
    print(f"snapshot: {payload['snapshot_path']}")
    print(f"known_urls: {payload['known_urls_path']} ({payload['known_url_count']})")
    print("scraper:", " ".join(payload["scraper_command"]))
    print("ingest:", " ".join(payload["ingest_command"]))


if __name__ == "__main__":
    raise SystemExit(main())
