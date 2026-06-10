# Decision Log

## 2026-06-08

### Observation

The existing政采情报库 project is a traditional Python/Node scraping prototype stored inside an OpenClaw workspace. It can collect and store procurement notices, but it does not use OpenClaw-native Agent identity, runtime boundaries, internal Skills, or conversational workflow design.

### Decision

Redesign the project as an OpenClaw sub-agent workspace with internal Skills.

### Reason

The user wants the system to serve文字新闻网业务部门工作人员 through DingTalk group briefs and interactive project Q&A. This requires a persistent role with domain-specific judgment, tone, memory, boundaries and ongoing responsibility. A standalone Skill or script project would not capture the product's core value.

### Impact

Future coding agents should treat the Agent as the product主体. The old collector/parser code may be used as reference, but should not dictate the new architecture. Implementation should begin from `docs/project_spec.md` and `docs/openclaw-contract.md`.

## 2026-06-08

### Observation

The user confirmed that first version scope should be: 情报发现 + 项目研判 + 简报 + 问答.

### Decision

Exclude投标执行、自动报名、投标文件生成、成交历史深度分析 and frontend dashboard from first version.

### Reason

The first release should prove the highest-value daily workflow: detect relevant Zhejiang procurement opportunities, explain why they matter, brief the DingTalk group and answer follow-up questions.

### Impact

The Agent must refuse or redirect execution requests that go beyond intelligence support. Historical成交 analysis remains a future internal Skill after the first version is stable.

## 2026-06-08

### Observation

The original media keyword taxonomy covered advertising, video,融媒,传播 and文化创意. The user added first-class focus categories: 信息化建设、网站建设、新媒体运营与运维、视频拍摄 and GEO 类项目.

### Decision

Use a two-tier category model:

- Core opportunities: 网站建设、新媒体运营与运维、视频拍摄、融媒体/传播服务、GEO 类项目.
- Edge opportunities: 信息化建设、系统运维、数据平台、活动策划、广告制作、宣传物料.

### Reason

Information technology procurement is broad and often unsuitable for a media business department unless it contains media, content, website, operation, communication, digital display or GEO evidence.

### Impact

The classifier must avoid promoting generic信息化项目 to A/B without concrete media-relevant deliverables.

## 2026-06-08

### Observation

The first implementation slice needs to prove procurement intelligence behavior before live collection, storage, DingTalk sending or OpenClaw runtime deployment.

### Decision

Implement a pure Python core under `src/procurement_intel/` for notice classification, opportunity scoring, DingTalk-ready brief rendering and bounded Q&A.

### Reason

These modules are deterministic, fixture-testable and directly support the Agent's first-version responsibilities without requiring network access, secrets or runtime workspace changes.

### Impact

`scripts/validate.sh` now runs the Python test suite with `PYTHONPATH=src`. Live collectors, persistence and DingTalk adapters remain future implementation slices.

## 2026-06-08

### Observation

The user asked for the next step after confirming that full real-data end-to-end testing needs collection and parsing.

### Decision

Add a public-page collector/parser slice and a manual `scripts/smoke_real_data.py` command that fetches a small number of public Zhejiang procurement notices, parses them into `Notice` records, then runs classification, scoring and brief rendering.

### Reason

This provides a half-real E2E path with no login, no CAPTCHA bypass, no DingTalk secrets and no OpenClaw runtime deployment. It tests real page compatibility while keeping default validation deterministic.

### Impact

`bash scripts/validate.sh` remains fixture-based. Real-data smoke tests must be run manually and interpreted with care because public website availability and page structures can change.

## 2026-06-08

### Observation

The user confirmed the primary monitoring target:

```text
https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement
```

The target page returns a JavaScript-rendered Zhejiang Government Procurement shell in static HTML. The shell exposes `siteId=110`, `purchaseNoticeParentId=600007`, `noticeArticleUrl=/site/detail`, and a candidate front-end endpoint `/magic/front/service/static/zcy.secondpagesearchlist.getSearchList/api`.

### Decision

Treat that URL as the canonical first monitoring source and keep it as `TARGET_MONITOR_URL` in the collector module.

### Reason

The user explicitly identified this page as the target website. Future implementation should focus on this source rather than drifting to national procurement pages or third-party mirrors.

### Impact

The current smoke script can diagnose the target page and can run real detail-page tests, but full list harvesting still needs the target site's front-end list API request shape or a browser-based collector.

## 2026-06-08

### Observation

OpenClaw already has `workspace-info-fetcher` with a `browser-fetch` Skill and a runtime script directory `/home/ai/.openclaw/workspace/scripts/zfcg-scraper` containing Puppeteer-based Zhejiang procurement scrapers.

### Decision

Add a local adapter that consumes JSON output from the existing Zhejiang procurement scraper and converts it into this project's `Notice` records.

### Reason

The procurement intelligence Agent should not duplicate browser automation if OpenClaw's fetcher stack can solve dynamic collection. This project should own classification, scoring, brief rendering and Q&A; the fetcher should own dynamic collection.

### Impact

`scripts/smoke_real_data.py` supports `--zfcg-json`. This enables a safe handoff path from OpenClaw collection output into the local intelligence pipeline without directly running or mutating runtime scraper state.

## 2026-06-08

### Observation

A controlled runtime `zfcg-scraper` run produced 48 scraped rows from the target site, but only 16 unique keys. The same visible list appeared under three categories, and a navigation item named `网站工作年度报表` was included.

Static detail-page fetches succeeded at the HTTP level but returned the JavaScript-rendered site shell, not the procurement detail fields.

### Decision

Add adapter-level cleaning to remove known navigation noise and deduplicate by URL. Add optional smoke detail enrichment with progress output and per-detail timeout, but keep browser-based detail extraction as the production direction.

### Reason

The intelligence pipeline should not score duplicate rows or navigation artifacts. Static detail fetching is useful as a diagnostic, but it cannot be relied on for fields such as buyer, budget and deadline when the detail page is rendered client-side.

### Impact

`load_zfcg_scraper_notices()` now returns cleaned unique notices. `scripts/smoke_real_data.py --enrich-details` can attempt detail enrichment, but robust detail completion should be delegated to OpenClaw `browser-fetch` or an enhanced Puppeteer scraper.

## 2026-06-08

### Observation

The controlled scrape produced non-empty data, but non-empty does not mean high quality. The first real output had duplicate category rows, navigation noise and missing buyer/budget/deadline fields.

### Decision

Add a scrape-quality evaluator for `zfcg-scraper` JSON output.

### Reason

The Agent needs to distinguish "target site can be reached" from "data is good enough for procurement intelligence." Quality metrics should be explicit and repeatable.

### Impact

`scripts/evaluate_scrape_quality.py` reports raw count, cleaned count, duplicate count, noise count, detail URL coverage, media relevance, opportunity distribution, missing fields, warnings and a `PASS/WARN/FAIL` grade.

## 2026-06-09

### Observation

The dual-column collector and daily pipeline now produce validated artifacts from public Zhejiang procurement data:

- `cleaned_notices.json`
- `opportunity_cards.json`
- `quality_report.json`
- `daily_brief.md`

The Agent skills still need a stable operational contract before runtime deployment.

### Decision

Treat `scripts/zfcg_browser_scraper.js` and `scripts/run_daily_pipeline.py` as the documented Agent tool-layer workflow for the first deployable capability. Use the latest generated `opportunity_cards.json` as the deterministic data source for procurement Q&A.

### Reason

This preserves a clear boundary between public data collection, deterministic intelligence scoring and bounded conversational answers. It also keeps runtime deployment conservative while the final OpenClaw invocation mechanism remains unconfirmed.

### Impact

The Agent skill README files now document inputs, defaults, outputs, acceptance sample, and safety boundaries. Deployment remains blocked until tool-layer packaging and runtime target are explicitly approved.

## 2026-06-10

### Observation

The deployed runtime and the development repository now operate on different machines. The runtime server is `100.91.229.7`, and runtime-side fixes may be pushed back to GitHub. The user also clarified future product directions around成交结果, lifecycle tracking, database storage, buyer/supplier profiles, n8n boundaries and historical QA.

### Decision

Record future requirements in `docs/future_requirements.md`. Treat SQLite as the recommended first storage layer, keep n8n out of the scraping core, and prioritize成交结果采集, project lifecycle linking, buyer/supplier profiles, price benchmarks and system health reports.

### Reason

The current Agent is useful as a daily opportunity radar. To become a durable procurement intelligence system, it needs a long-term fact store and lifecycle data. However, the next phase should remain conservative: local SQLite and deterministic scripts first, Supabase/Postgres and n8n orchestration later only when multi-user or remote access requirements become concrete.

### Impact

Future coding agents should read `docs/future_requirements.md` before implementing post-MVP upgrades. Before editing code, agents must pull from GitHub to avoid overwriting runtime-side changes.

## 2026-06-10

### Observation

The user reported that real-time full collection plus brief generation can time out when the daily notice volume is large. The proposed runtime model is hourly collection into local storage, followed by scheduled AM/PM brief generation from already-collected data.

### Decision

Adopt SQLite-backed hourly collection as the next upgrade direction. Save the implementation plan in `docs/superpowers/plans/2026-06-10-sqlite-hourly-collection.md`.

### Reason

Brief generation should not depend on a browser scrape completing at the brief deadline. SQLite provides a local fact store for deduplication, incremental detail enrichment, AM/PM push state, and later成交结果/lifecycle/profile features without introducing Supabase or another external service too early.

### Impact

The next implementation should first build SQLite storage and hourly ingestion, then switch AM/PM brief generation to read from SQLite. The current real-time `full_collect_and_brief.js` path should remain as a fallback until the SQLite flow has passed smoke testing on the runtime server.
