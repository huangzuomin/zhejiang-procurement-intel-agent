# TOOLS.md

## Tool Notes

This file documents intended tool usage. It does not grant tool access.

## Intended Tool Layer

- Collector: `scripts/cdp_scrape_bids.js` fetches public Zhejiang Government Procurement bid announcements via CDP WebSocket (auto-pagination, date filter, saves to `data/latest_bids.json`). Reuse pattern for intentions.
- Pipeline: `scripts/full_collect_and_brief.js --mode am|pm|full --today YYYY-MM-DD` reads intentions + bids, enriches via detail API (batch 15, 2s gap), classifies, scores, generates brief, saves to `reports/latest_daily_pipeline/`. AM mode also creates `data/latest_scrape_am.json` snapshot for PM diff.
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
- CDP scrape requires browser tab open on `zfcg.czt.zj.gov.cn`. CDP endpoint: `http://127.0.0.1:18800/json`.
- Do not use login-state scraping, CAPTCHA bypass or private-data collection.
- Do not submit procurement forms, register tenders, upload bid files, pay fees or sign contracts.
- Do not hard-code DingTalk secrets, webhook URLs, tokens or cookies.
- If a tool fails, report the failure and preserve partial evidence instead of fabricating results.
- DingTalk group: target `cid3eI/7oNrlJfnFadwzoQitw==`, accountId `zhejiang_procurement`. Message limit ~20000 chars; truncate deadline lists.
