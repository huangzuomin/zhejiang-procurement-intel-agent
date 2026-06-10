# Runtime Schedule

## Current Schedule Version

```text
schedule-v0.2.0
```

This schedule matches the SQLite hourly collection architecture.

## Runtime Target

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

Runtime server:

```text
100.91.229.7
```

## Enabled Jobs

### Hourly Collection

Recommended window:

```text
08:05, 09:05, 10:05, 11:05, 12:05, 13:05, 14:05, 15:05, 16:05, 17:05, 18:05
```

Command:

```bash
python3 scripts/run_hourly_collection.py --today $(date +%F) --hour $(date +%H) --db-path data/procurement_intel.db
```

Rules:

- This is the only scheduled job that should launch browser collection.
- Do not use `--include-historical` in this job.
- Keep `data/snapshots/` for replay and audit.

### AM Brief

Recommended time:

```text
09:20
```

Command:

```bash
python3 scripts/run_brief_from_db.py --mode am --today $(date +%F) --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/am
```

After DingTalk push success:

```bash
python3 scripts/run_brief_from_db.py --mode am --today $(date +%F) --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/am --record-push-success
```

Rules:

- AM brief generation must not launch browser collection.
- Only record push success after the push channel confirms success.

### PM Brief

Recommended time:

```text
15:20
```

Command:

```bash
python3 scripts/run_brief_from_db.py --mode pm --today $(date +%F) --since-brief am --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/pm
```

Rules:

- PM brief generation must not launch browser collection.
- PM should not repeat A/B focus opportunities recorded as successfully pushed in AM.

### Health Report

Recommended time:

```text
18:30
```

Command:

```bash
python3 scripts/run_health_report.py --today $(date +%F) --db-path data/procurement_intel.db --output reports/$(date +%F)/health_report.json
```

## Schedule Change Rules

- Every runtime schedule change must update this file.
- Every runtime schedule change must append `docs/deploy_log.md`.
- Do not silently replace hourly SQLite collection with real-time AM/PM scraping.
- Keep old live JSON pipeline only as manual fallback.

## Fallback Schedule

Use only when the SQLite path is blocked:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/$(date +%F)/zfcg-browser-two-columns-30.json
python3 scripts/run_daily_pipeline.py reports/$(date +%F)/zfcg-browser-two-columns-30.json --today $(date +%F) --output-dir reports/$(date +%F)/daily-pipeline
```

Fallback use must be recorded in the deploy log or incident notes.
