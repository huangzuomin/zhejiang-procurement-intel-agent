# SQLite Hourly Collection Runbook

## Purpose

This runbook describes the preferred runtime flow for the Zhejiang procurement intelligence Agent after the SQLite hourly collection upgrade.

The goal is to avoid timeout-prone "collect everything at brief time" behavior. Hourly jobs collect and persist public notices throughout the day. AM/PM brief jobs read the local SQLite database and do not launch browser scraping.

## Runtime Schedule

Recommended first schedule:

- Hourly collection: every hour during business hours, for example 08:00-18:00.
- AM brief: after at least one successful morning collection, for example 09:00.
- PM brief: after afternoon collection, for example 15:00.
- Health report: after AM and PM brief generation, or at end of day.

Use the runtime server clock and record the date explicitly as `YYYY-MM-DD`.

## Hourly Collection

Run one collection hour:

```bash
python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db
```

Default behavior:

- Writes known URLs to `data/runtime/<date>/known_urls.txt`.
- Runs `scripts/zfcg_browser_scraper.js` for `intention,bid`.
- Saves raw scraper snapshot to `data/snapshots/<date>/<HH>.json`.
- Ingests the snapshot into SQLite through `scripts/run_hourly_ingest.py`.
- Skips detail enrichment for URLs already known for the day.
- In normal hourly mode, ingests only notices whose `publish_date` equals `--today`.
- If a known URL skips detail enrichment, existing non-empty buyer, budget, deadline and opportunity score are preserved.

Dry-run without browser launch:

```bash
python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db --dry-run --json
```

## AM Brief

Generate the morning brief from already-collected SQLite data:

```bash
python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am
```

The AM brief summarizes all stored notices for the day, expands A/B focus opportunities, and keeps C/D items as distribution counts instead of noisy detail lists.

After the AM brief has actually been pushed successfully, record the pushed A/B focus items:

```bash
python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am --record-push-success
```

Only use `--record-push-success` after the outbound channel reports success. Do not record it for failed or skipped DingTalk sends.

## PM Brief

Generate the afternoon incremental brief from SQLite:

```bash
python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm
```

The PM brief should only expand unpushed A/B focus opportunities. It should not repeat AM focus items that have successful `push_events` for the same date.

## Bootstrap and Backfill

First-day cutover risk: an empty SQLite database plus a high collection limit can see historical list items. Normal hourly ingestion filters those out by default because only `publish_date == --today` is accepted.

For controlled backfill only, ingest an existing snapshot explicitly:

```bash
python3 scripts/run_hourly_ingest.py <snapshot.json> --today <date> --db-path data/procurement_intel.db --include-historical --run-type backfill --json
```

Backfill rules:

- Run backfill before enabling scheduled AM/PM push.
- Review health and brief output before recording push success.
- Do not use `--include-historical` in the normal hourly schedule.
- Keep the backfill snapshot and command output for audit.

## Health Report

Generate the collection health report:

```bash
python3 scripts/run_health_report.py --today <date> --db-path data/procurement_intel.db --output reports/<date>/health_report.json
```

Status rules:

- `PASS`: at least one successful hourly run, no failed hourly runs, and raw count meets threshold.
- `WARN`: successful run exists, but volume is low or one or more hourly runs failed.
- `FAIL`: no successful hourly collection for the day, or SQLite health check fails.

## Failure Behavior

- Scraper failure: `run_hourly_collection.py` records a failed `fetch_runs` row and exits nonzero.
- Ingest failure: the command exits nonzero and keeps the raw snapshot for debugging.
- Brief generation failure: do not mark DingTalk push as successful.
- Health `WARN` or `FAIL`: send or surface the warning before relying on the brief.

Never delete existing snapshots during a failed run. They are operational evidence.

## Rollback

If the SQLite flow is not healthy on the runtime server, use the previous live collection pipeline as a fallback:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/<date>/zfcg-browser-two-columns-30.json
python3 scripts/run_daily_pipeline.py reports/<date>/zfcg-browser-two-columns-30.json --today <date> --output-dir reports/<date>/daily-pipeline
```

`scripts/full_collect_and_brief.js` may remain available during transition, but it should not be the default high-volume scheduled path after SQLite cutover.

## Data Retention

Runtime data is local operational state and should not be committed:

- `data/procurement_intel.db`
- `data/runtime/`
- `data/snapshots/`
- `reports/`
- logs and any DingTalk/runtime secrets

Recommended retention:

- SQLite database: keep and back up before deployment changes.
- Raw snapshots: keep at least 14 days during stabilization.
- Reports: keep at least 30 days if disk allows.
- Failed-run evidence: keep until the cause is understood.

## Safety Boundaries

- Only collect public Zhejiang Government Procurement pages.
- Do not log in.
- Do not bypass CAPTCHA.
- Do not submit forms.
- Do not hard-code DingTalk tokens, cookies, secrets or webhook URLs.
- Do not modify `~/.openclaw` unless the user explicitly starts an approved deployment task.
