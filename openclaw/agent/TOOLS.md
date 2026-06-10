# TOOLS.md

## Tool Notes

This file documents intended tool usage. It does not grant tool access.

## Intended Tool Layer

- Hourly collector: `python3 scripts/run_hourly_collection.py --today YYYY-MM-DD --hour HH --db-path data/procurement_intel.db` writes known URLs, runs `scripts/zfcg_browser_scraper.js` for `intention,bid`, saves `data/snapshots/<date>/<hour>.json`, then ingests the snapshot into SQLite.
- Snapshot ingest: `python3 scripts/run_hourly_ingest.py data/snapshots/<date>/<hour>.json --today YYYY-MM-DD --db-path data/procurement_intel.db --json` converts scraper JSON into cleaned notices, opportunity cards, fetch runs and quality reports.
- AM brief from DB: `python3 scripts/run_brief_from_db.py --mode am --today YYYY-MM-DD --db-path data/procurement_intel.db --output-dir reports/<date>/am`.
- PM brief from DB: `python3 scripts/run_brief_from_db.py --mode pm --today YYYY-MM-DD --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm`.
- Legacy transition pipeline: `scripts/full_collect_and_brief.js --mode am|pm|full --today YYYY-MM-DD` remains runnable during cutover, but should not be the default high-volume scheduled path because it collects and briefs in the same run.
- Parser: normalize notice title, URL, buyer, budget, deadline, region, type, source column and raw content.
- Classifier: identify media-relevant categories and evidence.
- Scorer: assign A/B/C/D opportunity class, risk tags and column-aware recommended actions.
- Briefing renderer: produce column-aware daily messages and DingTalk-ready summaries.
- QA: `procurement_intel.qa.answer_question_from_cards_file` answers bounded questions from the latest `opportunity_cards.json`.
- DingTalk adapter: send outbound messages and process approved inbound questions.
- Storage: persist notices, opportunity cards, feedback and processing status.

## Rules

- Do not invent tools.
- Do not invent command flags.
- Do not run destructive commands without explicit permission.
- Prefer documented scripts over ad-hoc shell commands.
- Default collection targets both `采购意向公开` (intentions) and `招标公告` (bids) for the target date.
- Scheduled AM/PM brief generation must read SQLite and must not launch browser collection at brief time.
- Do not use login-state scraping, CAPTCHA bypass or private-data collection.
- Do not submit procurement forms, register tenders, upload bid files, pay fees or sign contracts.
- Do not hard-code DingTalk secrets, webhook URLs, tokens or cookies.
- If a tool fails, report the failure and preserve partial evidence instead of fabricating results.
- DingTalk group: target `cid3eI/7oNrlJfnFadwzoQitw==`, accountId `zhejiang_procurement`. Message limit ~20000 chars; truncate deadline lists.
