# TOOLS.md

## Tool Notes

This file documents intended tool usage. It does not grant tool access.

## Intended Tool Layer

- Collector: `scripts/zfcg_browser_scraper.js` fetches public Zhejiang Government Procurement notices from `采购意向公开` and `招标公告`.
- Pipeline: `scripts/run_daily_pipeline.py` writes cleaned notices, opportunity cards, quality report, summary, and daily brief artifacts.
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
- Default collection is `--targets intention,bid --limit 30 --detail-limit 30`.
- Do not use login-state scraping, CAPTCHA bypass or private-data collection.
- Do not submit procurement forms, register tenders, upload bid files, pay fees or sign contracts.
- Do not hard-code DingTalk secrets, webhook URLs, tokens or cookies.
- If a tool fails, report the failure and preserve partial evidence instead of fabricating results.
