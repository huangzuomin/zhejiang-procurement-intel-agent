# SQLite Hourly Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace timeout-prone real-time AM/PM full collection with SQLite-backed hourly collection, incremental detail enrichment, and scheduled brief generation from already-collected local data.

**Architecture:** Split the runtime into two independent flows. The hourly flow collects list data, skips known URLs, enriches only new or stale notices, classifies/scores them, and persists them in SQLite. The brief flow never launches a browser; it reads SQLite rows for the requested day/window and renders AM full or PM incremental DingTalk briefs.

**Tech Stack:** Python standard library `sqlite3`, existing `procurement_intel` modules, existing Node scraper, pytest, local JSON/Markdown report artifacts.

---

## Operating Rules

- Before implementation, run `git pull --ff-only origin main`.
- Do not edit `~/.openclaw/`.
- Do not commit `data/`, `reports/`, SQLite database files, snapshots, cookies, secrets, or runtime logs.
- Keep JSON/Markdown outputs for observability, but treat SQLite as the source of truth.
- First implementation target is SQLite only. Do not introduce Supabase/Postgres in this plan.
- Keep existing `scripts/full_collect_and_brief.js` runnable during the transition, but mark it as legacy once DB brief generation is verified.

## Target Runtime Flow

```text
Hourly collection, e.g. 08:00-18:00
  node scripts/zfcg_browser_scraper.js --targets intention,bid --limit <N> --known-urls-file <file> --output data/snapshots/<date>/<hour>.json
  python3 scripts/run_hourly_ingest.py data/snapshots/<date>/<hour>.json --db-path data/procurement_intel.db --today <date>

AM brief, e.g. 09:00
  python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am

PM brief, e.g. 15:00
  python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm
```

## File Structure

- Create `src/procurement_intel/storage.py`
  - Owns SQLite connection, schema creation, upserts, fetch run records, brief push records, and query helpers.
- Create `src/procurement_intel/hourly_ingestion.py`
  - Converts scraper JSON payloads into notices/cards and writes them to storage.
- Create `src/procurement_intel/db_briefing.py`
  - Queries stored cards and renders AM/PM brief inputs.
- Create `scripts/run_hourly_ingest.py`
  - CLI wrapper for ingesting a scraper JSON snapshot into SQLite.
- Create `scripts/run_brief_from_db.py`
  - CLI wrapper for generating AM/PM briefs from SQLite.
- Modify `scripts/zfcg_browser_scraper.js`
  - Add known-URL support so old URLs are listed but not detail-enriched again.
- Modify `scripts/full_collect_and_brief.js`
  - Keep `generateBrief()` as shared formatting logic if useful; avoid adding more collection responsibility.
- Modify `.gitignore`
  - Keep `data/` ignored; add explicit SQLite patterns if needed.
- Modify docs:
  - `docs/future_requirements.md`
  - `docs/decision_log.md`
  - `openclaw/agent/TOOLS.md`
- Tests:
  - Create `tests/test_storage.py`
  - Create `tests/test_hourly_ingestion.py`
  - Create `tests/test_db_briefing.py`
  - Extend `tests/test_zfcg_browser_scraper_cli.py`

---

## Iteration 1: SQLite Storage Foundation

**Purpose:** Establish the durable local fact store without changing live collection behavior.

**Files:**
- Create: `src/procurement_intel/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing schema initialization test**

Create `tests/test_storage.py` with a test that initializes a temporary database and asserts required tables exist.

```python
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
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_storage.py::test_initializes_required_tables -v
```

Expected: FAIL because `procurement_intel.storage` does not exist.

- [ ] **Step 3: Implement minimal SQLiteStore schema**

Create `src/procurement_intel/storage.py` with a small `SQLiteStore` class.

Required schema decisions:

- `notices.detail_url` is unique.
- `notices.source_column` stores `intention` or `bid`.
- `notices.first_seen_at` and `notices.last_seen_at` are ISO timestamps.
- `opportunity_cards.notice_id` references `notices.id`.
- `push_events.notice_id` stores which brief mode has pushed a notice.

Suggested initial table set:

```sql
create table if not exists fetch_runs (
  id integer primary key autoincrement,
  run_id text not null unique,
  run_type text not null,
  started_at text not null,
  finished_at text,
  source text,
  raw_count integer not null default 0,
  new_count integer not null default 0,
  enriched_count integer not null default 0,
  status text not null default 'running',
  error text
);

create table if not exists notices (
  id integer primary key autoincrement,
  detail_url text not null unique,
  title text not null,
  notice_type text,
  source_column text,
  source_column_path text,
  source_category_code text,
  publish_date text,
  region text,
  category_code text,
  buyer text,
  budget real,
  deadline text,
  project_name text,
  first_seen_at text not null,
  last_seen_at text not null,
  latest_fetch_run_id text
);

create table if not exists notice_details (
  notice_id integer primary key,
  raw_detail_text text,
  contact text,
  phone text,
  detail_enriched_at text,
  parser_version text not null,
  foreign key(notice_id) references notices(id)
);

create table if not exists opportunity_cards (
  notice_id integer primary key,
  opportunity_class text not null,
  primary_category text,
  is_media_relevant integer not null,
  confidence real,
  reasons_json text not null,
  risks_json text not null,
  missing_fields_json text not null,
  recommended_action text,
  scored_at text not null,
  scorer_version text not null,
  foreign key(notice_id) references notices(id)
);

create table if not exists push_events (
  id integer primary key autoincrement,
  notice_id integer,
  brief_date text not null,
  brief_mode text not null,
  pushed_at text not null,
  status text not null,
  foreign key(notice_id) references notices(id)
);

create table if not exists quality_reports (
  id integer primary key autoincrement,
  fetch_run_id text not null,
  report_json text not null,
  created_at text not null
);
```

- [ ] **Step 4: Run the schema test and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/procurement_intel/storage.py tests/test_storage.py
git commit -m "feat: add sqlite storage foundation"
```

---

## Iteration 2: Idempotent Notice and Opportunity Upserts

**Purpose:** Make SQLite useful for de-duplication and incremental state before adding scheduler behavior.

**Files:**
- Modify: `src/procurement_intel/storage.py`
- Modify: `tests/test_storage.py`

- [ ] **Step 1: Write failing notice upsert test**

Add a test proving the same URL updates one row instead of inserting duplicates.

```python
from procurement_intel.models import Notice


def test_upserts_notice_by_detail_url(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()

    notice = Notice(
        title="政务新媒体运营服务采购意向",
        url="https://zfcg.czt.zj.gov.cn/site/detail?articleId=abc",
        notice_type="采购意向公开",
        publish_date="2026-06-10",
        region="杭州",
        buyer="杭州市某单位",
        budget=200000,
        deadline=None,
        source_column="intention",
    )

    first_id = store.upsert_notice(notice, fetch_run_id="run-1", seen_at="2026-06-10T09:00:00")
    second_id = store.upsert_notice(notice, fetch_run_id="run-2", seen_at="2026-06-10T10:00:00")

    assert first_id == second_id
    assert store.count_notices() == 1
    stored = store.get_notice_by_url(notice.url)
    assert stored["latest_fetch_run_id"] == "run-2"
    assert stored["first_seen_at"] == "2026-06-10T09:00:00"
    assert stored["last_seen_at"] == "2026-06-10T10:00:00"
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_storage.py::test_upserts_notice_by_detail_url -v
```

Expected: FAIL because upsert helpers are not implemented.

- [ ] **Step 3: Implement notice upsert helpers**

Add these methods to `SQLiteStore`:

- `upsert_notice(notice, fetch_run_id: str, seen_at: str) -> int`
- `count_notices() -> int`
- `get_notice_by_url(url: str) -> dict | None`
- `known_urls_for_date(today: str) -> set[str]`

Implementation rule:

- Insert new URLs with `first_seen_at = seen_at`.
- Existing URLs keep original `first_seen_at` and update mutable fields plus `last_seen_at`.

- [ ] **Step 4: Add and test opportunity card upsert**

Add a test that scores a notice, upserts the card, and updates it idempotently.

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/procurement_intel/storage.py tests/test_storage.py
git commit -m "feat: add sqlite notice and card upserts"
```

---

## Iteration 3: Hourly Ingestion From Existing Scraper JSON

**Purpose:** Persist current scraper outputs to SQLite without changing the live browser collector yet.

**Files:**
- Create: `src/procurement_intel/hourly_ingestion.py`
- Create: `scripts/run_hourly_ingest.py`
- Create: `tests/test_hourly_ingestion.py`

- [ ] **Step 1: Write failing ingestion test**

Create a fixture payload with one known URL and one new URL. Assert only the new row is counted as new on second ingest.

```python
import json

from procurement_intel.hourly_ingestion import ingest_scraper_payload
from procurement_intel.storage import SQLiteStore


def test_hourly_ingestion_is_idempotent(tmp_path):
    db_path = tmp_path / "procurement_intel.db"
    payload = {
        "source": "zfcg_browser_scraper",
        "scraped_at": "2026-06-10T09:00:00",
        "notices": [
            {
                "title": "门户网站建设与新媒体运营服务公开招标公告",
                "detail_url": "https://zfcg.czt.zj.gov.cn/site/detail?articleId=bid",
                "notice_type": "招标公告",
                "publish_date": "2026-06-10",
                "region": "浙江",
                "source_column": "bid",
                "buyer": "浙江某单位",
                "budget": 600000,
                "deadline": "2026-06-30",
                "raw_detail_text": "采购需求：门户网站建设、内容管理和新媒体运营。",
            }
        ],
    }

    first = ingest_scraper_payload(payload, db_path=db_path, today="2026-06-10", run_type="hourly")
    second = ingest_scraper_payload(payload, db_path=db_path, today="2026-06-10", run_type="hourly")

    assert first.new_count == 1
    assert second.new_count == 0
    assert SQLiteStore(db_path).count_notices() == 1
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_hourly_ingestion.py -v
```

Expected: FAIL because `hourly_ingestion.py` does not exist.

- [ ] **Step 3: Implement `ingest_scraper_payload`**

Implementation responsibilities:

- Initialize SQLite schema.
- Convert payload with `zfcg_scraper_payload_to_notices`.
- For each notice:
  - upsert notice
  - classify
  - score
  - upsert opportunity card
- Write a `fetch_runs` row.
- Write a `quality_reports` row using `evaluate_zfcg_scraper_payload`.

Return a dataclass:

```python
@dataclass(frozen=True)
class HourlyIngestResult:
    run_id: str
    raw_count: int
    cleaned_count: int
    new_count: int
    updated_count: int
    opportunity_counts: dict[str, int]
    quality_grade: str
```

- [ ] **Step 4: Implement `scripts/run_hourly_ingest.py`**

CLI contract:

```bash
python3 scripts/run_hourly_ingest.py <scraper-json> --today YYYY-MM-DD --db-path data/procurement_intel.db --json
```

Expected JSON output contains:

- `run_id`
- `raw_count`
- `new_count`
- `updated_count`
- `quality_grade`
- `opportunity_counts`

- [ ] **Step 5: Run focused tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_hourly_ingestion.py tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/procurement_intel/hourly_ingestion.py scripts/run_hourly_ingest.py tests/test_hourly_ingestion.py
git commit -m "feat: ingest hourly scraper snapshots into sqlite"
```

---

## Iteration 4: Known-URL Aware Browser Collection

**Purpose:** Stop repeatedly detail-enriching hundreds of already-seen notices.

**Files:**
- Modify: `scripts/zfcg_browser_scraper.js`
- Modify: `tests/test_zfcg_browser_scraper_cli.py`

- [ ] **Step 1: Write failing CLI test for known URL file**

Add a Node CLI unit test that verifies argument parsing exposes a known URL file.

```python
def test_zfcg_browser_scraper_accepts_known_urls_file() -> None:
    js = """
    const scraper = require('./scripts/zfcg_browser_scraper.js');
    const args = scraper.parseArgs(['--known-urls-file', 'data/known_urls.txt', '--no-details']);
    console.log(JSON.stringify({ knownUrlsFile: args.knownUrlsFile, details: args.details }));
    """
    result = subprocess.run(["node", "-e", js], cwd=ROOT, check=True, capture_output=True, text=True)

    payload = json.loads(result.stdout)
    assert payload["knownUrlsFile"] == "data/known_urls.txt"
    assert payload["details"] is False
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_zfcg_browser_scraper_cli.py::test_zfcg_browser_scraper_accepts_known_urls_file -v
```

Expected: FAIL if `parseArgs` is not exported or `knownUrlsFile` is not supported.

- [ ] **Step 3: Export parser helpers safely**

Modify `scripts/zfcg_browser_scraper.js` so it follows the same safe pattern as `full_collect_and_brief.js`:

```js
if (require.main === module) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

module.exports = {
  parseArgs,
  extractBuyer,
  parseBudget,
};
```

This must not launch Puppeteer when required by tests.

- [ ] **Step 4: Implement known URL loading**

Add:

- `--known-urls-file <path>`
- `loadKnownUrls(filepath) -> Set`
- `isKnown = knownUrls.has(item.detail_url)`

Behavior:

- Always include list item in output with `known_url: true` if seen.
- Only call `fetchPortalDetail()` when `args.details` is true and URL is not known.
- Set `detail_skipped_reason: "known_url"` for skipped known URLs.

- [ ] **Step 5: Add behavior test for skip logic**

Add a pure function if needed:

```js
function shouldFetchDetail(item, args, knownUrls, index) {
  return args.details && index < args.detailLimit && !knownUrls.has(item.detail_url);
}
```

Test it from Python via `node -e`.

- [ ] **Step 6: Run scraper CLI tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_zfcg_browser_scraper_cli.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/zfcg_browser_scraper.js tests/test_zfcg_browser_scraper_cli.py
git commit -m "feat: skip detail enrichment for known zfcg urls"
```

---

## Iteration 5: DB-Backed AM and PM Brief Generation

**Purpose:** At brief time, do not scrape. Read today's SQLite data and render concise AM/PM DingTalk messages.

**Files:**
- Create: `src/procurement_intel/db_briefing.py`
- Create: `scripts/run_brief_from_db.py`
- Create: `tests/test_db_briefing.py`
- Modify: `scripts/full_collect_and_brief.js` only if reusing `generateBrief`

- [ ] **Step 1: Write failing AM brief test**

Seed SQLite with A/B/D cards. Assert AM brief shows A/B only and omits D details.

```python
from procurement_intel.db_briefing import build_brief_from_db


def test_am_brief_reads_sqlite_and_omits_d_noise(seed_sqlite_store):
    message = build_brief_from_db(
        seed_sqlite_store.db_path,
        today="2026-06-10",
        mode="am",
    )

    assert "浙江政采情报日报" in message
    assert "A 1 / B 1 / C 0 / D 1" in message
    assert "门户网站建设" in message
    assert "融媒体建设" in message
    assert "教学一体机" not in message
```

- [ ] **Step 2: Write failing PM brief test**

Seed one A item as pushed in AM and one later B item as unpushed. Assert PM includes only the later B.

```python
def test_pm_brief_only_includes_unpushed_focus_items(seed_sqlite_store):
    message = build_brief_from_db(
        seed_sqlite_store.db_path,
        today="2026-06-10",
        mode="pm",
        since_brief="am",
    )

    assert "浙江政采情报增量" in message
    assert "下午新增" in message
    assert "新增B类项目" in message
    assert "上午已推送A类项目" not in message
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_db_briefing.py -v
```

Expected: FAIL because DB briefing module does not exist.

- [ ] **Step 4: Implement DB query helpers**

In `SQLiteStore`, add:

- `list_cards_for_date(today: str) -> list[dict]`
- `list_unpushed_focus_cards(today: str, brief_mode: str) -> list[dict]`
- `record_push_event(notice_id: int, brief_date: str, brief_mode: str, status: str, pushed_at: str) -> None`

Focus card means `opportunity_class in ("A", "B")`.

- [ ] **Step 5: Implement `build_brief_from_db`**

Rules:

- AM:
  - read all today cards
  - render A/B focus projects
  - summarize C/D counts only
- PM:
  - read only unpushed A/B cards after AM
  - if none, render status-only message
  - never repeat AM focus items
- Brief generation must not invoke Node, Puppeteer, or network.

- [ ] **Step 6: Implement `scripts/run_brief_from_db.py`**

CLI contract:

```bash
python3 scripts/run_brief_from_db.py --mode am --today 2026-06-10 --db-path data/procurement_intel.db --output-dir reports/2026-06-10/am
python3 scripts/run_brief_from_db.py --mode pm --today 2026-06-10 --since-brief am --db-path data/procurement_intel.db --output-dir reports/2026-06-10/pm
```

Outputs:

- `daily_brief.md`
- `summary.json`

- [ ] **Step 7: Run DB brief tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_db_briefing.py tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/procurement_intel/db_briefing.py scripts/run_brief_from_db.py tests/test_db_briefing.py src/procurement_intel/storage.py
git commit -m "feat: generate am pm briefs from sqlite"
```

---

## Iteration 6: Hourly Collection Orchestrator

**Purpose:** Provide one command for runtime scheduling that collects snapshots and ingests them.

**Files:**
- Create: `scripts/run_hourly_collection.py`
- Create: `tests/test_hourly_collection_cli.py`
- Modify: `docs/future_requirements.md`
- Modify: `openclaw/agent/TOOLS.md`

- [ ] **Step 1: Write failing dry-run CLI test**

The hourly orchestrator must support a dry-run mode that prints commands without launching Puppeteer.

```python
import json
import subprocess


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
    assert "zfcg_browser_scraper.js" in payload["scraper_command"][1]
    assert "run_hourly_ingest.py" in payload["ingest_command"][1]
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_hourly_collection_cli.py -v
```

Expected: FAIL because orchestrator does not exist.

- [ ] **Step 3: Implement dry-run orchestrator**

CLI contract:

```bash
python3 scripts/run_hourly_collection.py --today YYYY-MM-DD --hour HH --db-path data/procurement_intel.db --limit 300 --detail-limit 300 --json
```

Behavior:

- Write known URLs file from SQLite to `data/runtime/<date>/known_urls.txt`.
- Run scraper with `--known-urls-file`.
- Save raw snapshot to `data/snapshots/<date>/<hour>.json`.
- Run `scripts/run_hourly_ingest.py` on that snapshot.

- [ ] **Step 4: Add non-dry-run path with subprocess checks**

Rules:

- If scraper exits nonzero, record a failed fetch run and exit nonzero.
- If ingest exits nonzero, exit nonzero.
- Never delete previous snapshots.

- [ ] **Step 5: Run CLI tests**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_hourly_collection_cli.py -v
```

Expected: PASS.

- [ ] **Step 6: Update docs**

Update `docs/future_requirements.md` and `openclaw/agent/TOOLS.md` with:

```bash
python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db
python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am
python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm
```

- [ ] **Step 7: Commit**

```bash
git add scripts/run_hourly_collection.py tests/test_hourly_collection_cli.py docs/future_requirements.md openclaw/agent/TOOLS.md
git commit -m "feat: add hourly sqlite collection orchestrator"
```

---

## Iteration 7: Health Report and Runtime Readiness

**Purpose:** Make failures visible and keep brief generation reliable even if hourly collection partially fails.

**Files:**
- Modify: `src/procurement_intel/storage.py`
- Create: `src/procurement_intel/health.py`
- Create: `scripts/run_health_report.py`
- Create: `tests/test_health_report.py`
- Modify: `docs/deploy_manifest.md`
- Modify: `scripts/prepare_deploy_dry_run.py`

- [ ] **Step 1: Write failing health report test**

```python
from procurement_intel.health import build_health_report


def test_health_report_flags_low_collection_count(tmp_path):
    store = SQLiteStore(tmp_path / "procurement_intel.db")
    store.initialize()
    store.record_fetch_run(run_id="run-low", run_type="hourly", raw_count=0, new_count=0, enriched_count=0, status="success")

    report = build_health_report(store.db_path, today="2026-06-10", expected_min_raw_count=10)

    assert report["status"] == "WARN"
    assert "抓取量低于阈值" in report["warnings"]
```

- [ ] **Step 2: Run test and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_health_report.py -v
```

Expected: FAIL because health module does not exist.

- [ ] **Step 3: Implement health report**

Metrics:

- hourly run count
- raw count
- new count
- enriched count
- failed run count
- A/B/C/D distribution
- last successful run time

Statuses:

- `PASS`: collection and brief inputs look healthy
- `WARN`: partial failure or low volume
- `FAIL`: no successful runs for the day or DB unreadable

- [ ] **Step 4: Add health CLI**

```bash
python3 scripts/run_health_report.py --today 2026-06-10 --db-path data/procurement_intel.db --output reports/2026-06-10/health_report.json
```

- [ ] **Step 5: Update deploy dry-run**

Include new deployable scripts/modules:

- `scripts/run_hourly_collection.py`
- `scripts/run_hourly_ingest.py`
- `scripts/run_brief_from_db.py`
- `scripts/run_health_report.py`
- `src/procurement_intel/storage.py`
- `src/procurement_intel/hourly_ingestion.py`
- `src/procurement_intel/db_briefing.py`
- `src/procurement_intel/health.py`

- [ ] **Step 6: Run tests**

Run:

```bash
bash scripts/validate.sh
python3 scripts/prepare_deploy_dry_run.py --json
```

Expected:

- validate passes
- dry-run `forbidden_matches` is `[]`

- [ ] **Step 7: Commit**

```bash
git add src/procurement_intel/health.py scripts/run_health_report.py tests/test_health_report.py scripts/prepare_deploy_dry_run.py docs/deploy_manifest.md
git commit -m "feat: add sqlite collection health report"
```

---

## Iteration 8: Cutover Runbook

**Purpose:** Document how runtime should move from real-time full collection to hourly SQLite collection.

**Files:**
- Create: `docs/sqlite_hourly_collection_runbook.md`
- Modify: `openclaw/agent/MEMORY.md`
- Modify: `docs/decision_log.md`

- [ ] **Step 1: Write runbook**

Runbook sections:

- Runtime schedule
- Hourly collection command
- AM brief command
- PM brief command
- Health report command
- Failure behavior
- Rollback to current `full_collect_and_brief.js`
- Data retention policy

- [ ] **Step 2: Update Agent memory/tools**

Record:

- Hourly collection is preferred.
- Brief generation must read SQLite and must not launch browser collection.
- `full_collect_and_brief.js` is fallback/legacy after DB cutover.

- [ ] **Step 3: Run validation**

Run:

```bash
bash scripts/validate.sh
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs/sqlite_hourly_collection_runbook.md openclaw/agent/MEMORY.md docs/decision_log.md
git commit -m "docs: add sqlite hourly collection runbook"
```

---

## Final Verification

After all iterations:

```bash
git pull --ff-only origin main
bash scripts/validate.sh
python3 scripts/prepare_deploy_dry_run.py --json
```

Manual non-deploy smoke on development machine:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 5 --detail-limit 5 --output data/snapshots/$(date +%F)/smoke.json
python3 scripts/run_hourly_ingest.py data/snapshots/$(date +%F)/smoke.json --today $(date +%F) --db-path data/procurement_intel.db --json
python3 scripts/run_brief_from_db.py --mode am --today $(date +%F) --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/am
python3 scripts/run_brief_from_db.py --mode pm --today $(date +%F) --since-brief am --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/pm
python3 scripts/run_health_report.py --today $(date +%F) --db-path data/procurement_intel.db --output reports/$(date +%F)/health_report.json
```

Expected:

- Hourly ingest writes SQLite.
- Re-ingesting the same snapshot creates zero new notices.
- AM brief renders current A/B focus items.
- PM brief does not repeat AM items.
- PM no-new brief is status-only.
- Health report is PASS or WARN with explicit reason.
- No `data/`, `reports/`, or SQLite database files are staged.

## Self-Review

- Spec coverage: Covers SQLite storage, hourly collection, known URL skipping, AM/PM DB briefs, health report, docs, and deploy dry-run updates.
- Placeholder scan: No TBD/TODO placeholders are present.
- Scope check: 成交结果采集, buyer/supplier profiles, lifecycle matching, and Supabase migration are intentionally outside this first cutover plan. They should be implemented after SQLite hourly collection is stable.
- Type consistency: Main introduced names are `SQLiteStore`, `ingest_scraper_payload`, `HourlyIngestResult`, `build_brief_from_db`, and `build_health_report`.
