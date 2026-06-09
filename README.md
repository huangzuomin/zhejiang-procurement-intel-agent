# Zhejiang Procurement Intelligence Agent

OpenClaw-native Agent workspace and local tool layer for monitoring public Zhejiang Government Procurement notices, identifying media/digital business opportunities, generating daily briefs, and answering bounded questions from generated opportunity cards.

The project currently focuses on two public columns from Zhejiang Government Procurement:

- `采购意向公开`: early procurement signals for pre-positioning.
- `招标公告`: formal opportunities for immediate response review.

## What It Does

- Browser-collects public notices from the Zhejiang Government Procurement website.
- Completes list and detail fields including buyer, budget, deadline, region, category and raw detail text.
- Classifies notices for media/digital relevance.
- Scores opportunities as A/B/C/D.
- Generates a readable daily procurement opportunity brief.
- Produces deterministic `opportunity_cards.json` for follow-up Q&A.
- Keeps strict boundaries: no login scraping, no CAPTCHA bypass, no form submission, no bid execution.

## Repository Layout

```text
openclaw/agent/                  OpenClaw Agent identity, resources and internal skill docs
src/procurement_intel/           Deterministic local intelligence modules
scripts/zfcg_browser_scraper.js  Dual-column browser collector
scripts/run_daily_pipeline.py    End-to-end daily pipeline
scripts/query_opportunity_cards.py
scripts/prepare_deploy_dry_run.py
tests/                           Unit and acceptance tests
tests/fixtures/                  Safe public-data fixtures used by tests
docs/                            Design, deployment and audit documents
```

## Requirements

- Python 3.12+ or 3.14+
- Node.js 20+
- `pytest` for tests
- `puppeteer` for live browser collection

Install JavaScript dependency:

```bash
npm install
```

Install Python test dependency in your preferred environment:

```bash
python3 -m pip install pytest
```

The production Python tool layer currently uses only the standard library.

## Quick Start

Run validation:

```bash
bash scripts/validate.sh
```

Generate a daily brief from the included public-data fixture:

```bash
python3 scripts/run_daily_pipeline.py tests/fixtures/zfcg_browser_two_columns_60.json --today 2026-06-09 --output-dir reports/demo-daily-pipeline
```

Ask a bounded question from generated cards:

```bash
python3 scripts/query_opportunity_cards.py reports/demo-daily-pipeline/opportunity_cards.json "今天有哪些 A/B 机会？"
```

## Live Collection

The primary public monitoring URL is:

```text
https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement
```

Run a controlled dual-column collection:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/$(date +%F)/zfcg-browser-two-columns-30.json
```

Then run the daily pipeline:

```bash
python3 scripts/run_daily_pipeline.py reports/$(date +%F)/zfcg-browser-two-columns-30.json --today $(date +%F) --output-dir reports/$(date +%F)/daily-pipeline
```

Generated artifacts:

- `cleaned_notices.json`
- `opportunity_cards.json`
- `quality_report.json`
- `daily_brief.md`
- `summary.json`

## OpenClaw Packaging

This repository is a development workspace, not the runtime workspace.

Default proposed runtime target:

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

Recommended packaging scheme:

- `openclaw/agent/`
- `src/procurement_intel/`
- approved command wrappers in `scripts/`

Prepare a deployment dry run without copying runtime files:

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```

Do not deploy until `docs/delivery_audit_report.md` has been reviewed and a user explicitly authorizes deployment.

## Safety Boundaries

This project only processes public procurement information.

It does not:

- bypass login, CAPTCHA or access controls
- collect private/non-public procurement data
- submit forms
- register tenders
- upload bid files
- make payments
- sign contracts
- store DingTalk secrets or credentials

When data is missing, the Agent reports it as missing instead of inventing facts.

## Validation Status

Current repository validation:

```text
bash scripts/validate.sh
44 passed
Validation passed.
```

## License

MIT License. See [LICENSE](LICENSE).
