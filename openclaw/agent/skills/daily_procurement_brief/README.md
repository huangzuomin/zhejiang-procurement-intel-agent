# daily_procurement_brief

Generate the Zhejiang government procurement opportunity brief for today.

Use when the user asks for today's Zhejiang procurement opportunities, a daily brief, a weekly brief seed, or a DingTalk-ready opportunity summary.

## Default Monitoring Scope

- `采购意向公开`: early signals for pre-positioning and requirement discovery.
- `招标公告`: formal opportunities for immediate response review.

Default source URL:

```text
https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement
```

## Inputs

- `today`: scoring date, default to the current local date.
- `limit`: notices per column, default `30`.
- `detail_limit`: detail pages per column, default same as `limit`.
- `input_json`: optional existing scraper JSON. When present, skip live collection and run the pipeline on this file.
- `output_dir`: artifact directory, default under `reports/<date>/`.

## Local Commands

Collect the two default columns:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/<date>/zfcg-browser-two-columns-30.json
```

Run the intelligence pipeline:

```bash
python3 scripts/run_daily_pipeline.py reports/<date>/zfcg-browser-two-columns-30.json --today <date> --output-dir reports/<date>/daily-pipeline-sample
```

## Outputs

- `cleaned_notices.json`: cleaned notices with `source_column`, `source_column_path`, and `source_category_code`.
- `opportunity_cards.json`: classified/scored opportunity cards.
- `quality_report.json`: scrape quality and field coverage summary.
- `daily_brief.md`: readable daily opportunity brief.
- `summary.json`: artifact paths and headline counts.

## Brief Sections

- 招标公告重点机会
- 采购意向早期线索
- 媒体/数字化相关机会
- 字段缺失或风险提示

## Acceptance Sample

Use the checked real 60-notice sample:

```bash
python3 scripts/run_daily_pipeline.py reports/zfcg-2026-06-09/zfcg-browser-two-columns-30.json --today 2026-06-09 --output-dir reports/zfcg-2026-06-09/daily-pipeline-sample
```

Expected properties:

- `quality_grade` is `PASS`.
- The brief contains both `招标公告重点机会` and `采购意向早期线索`.
- The brief includes A/B/C/D opportunity distribution.
- `bid` cards use immediate-response recommendations.
- `intention` cards use early-follow-up recommendations.

## Safety Boundary

- Only collect public website data.
- Keep collection low frequency; default detail delay is controlled by the scraper.
- Do not bypass login, CAPTCHA, access controls, or anti-abuse mechanisms.
- Do not submit forms, register for tenders, upload bid documents, pay fees, or sign contracts.
- Do not invent budget, buyer, deadline, or undisclosed facts.
- Do not claim a DingTalk message was sent unless an approved adapter actually ran successfully.
