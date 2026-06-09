# Test Plan: 政采情报库 Agent

## Static Validation

- Command: `bash scripts/validate.sh`
- Expected result: validation passes without unresolved required files, missing Agent identity documents, failing tests, or forbidden deployable artifacts.

The validation script should check:

- `openclaw/agent/AGENTS.md` exists.
- `openclaw/agent/IDENTITY.md` exists.
- `openclaw/agent/SOUL.md` exists.
- `openclaw/agent/TOOLS.md` exists.
- `openclaw/agent/USER.md` exists.
- Internal skill directories exist for daily brief, notice evaluation, procurement Q&A and keyword strategy tuning.
- Required resources exist for taxonomy, scoring rules, risk rules and DingTalk message format.
- Python/Node code compiles or passes configured linters.
- Unit tests pass.
- Forbidden files are not included in the deployable package.

## Local Functional Validation

### Test: Public real-data smoke

- Command:
  ```bash
  python3 scripts/smoke_real_data.py --limit 5 --json
  ```
- Primary monitoring URL:
  ```text
  https://zfcg.czt.zj.gov.cn/site/category?parentId=600007&childrenCode=ZcyAnnouncement
  ```
- Expected result:
  - The script fetches public Zhejiang procurement list/detail pages without login.
  - Parsed notices are classified, scored and rendered into a DingTalk-ready brief.
  - Fetch or parse errors are reported explicitly and do not create fabricated cards.
- Notes:
  - This is a manual smoke test, not part of `bash scripts/validate.sh`, because public website availability and page structure can change.
  - The script does not send DingTalk messages, write runtime state or edit `~/.openclaw/`.
  - The primary monitoring page is JavaScript-rendered. Static HTML parsing may return no notice links; this is a known diagnostic state, not a successful full list harvest.

### Test: OpenClaw zfcg scraper JSON adapter

- Command:
  ```bash
  python3 scripts/smoke_real_data.py --zfcg-json tests/fixtures/zfcg_scraper_sample.json --limit 5 --json
  ```
- Expected result:
  - The script converts `zfcg-scraper` JSON output into local `Notice` records.
  - Converted notices run through classification, scoring and brief rendering.
  - Missing budget/deadline fields are surfaced as `信息不足` instead of fabricated.
- Notes:
  - This test consumes existing JSON only. It does not run the runtime scraper and does not write `/home/ai/.openclaw/workspace/data`.
  - Adapter cleaning removes known navigation noise such as `网站工作年度报表` and deduplicates repeated URLs across scraper categories.
  - Detail enrichment is available through `--enrich-details`, but Zhejiang procurement detail pages may also be JavaScript-rendered; browser-based detail extraction remains the preferred production path.

### Test: Scrape data quality evaluation

- Command:
  ```bash
  python3 scripts/evaluate_scrape_quality.py /path/to/zfcg-mvp-output.json --json
  ```
- Expected result:
  - Reports raw item count, cleaned notice count, duplicates, noise, detail URL coverage, media-relevant count, opportunity distribution and missing-field counts.
  - Grades output as `PASS`, `WARN` or `FAIL`.
  - Flags duplicate-heavy, noisy or detail-field-missing outputs instead of treating any non-empty scrape as successful.

### Test: Zhejiang procurement fixture ingestion

- Steps:
  1. Load fixture pages for Zhejiang procurement list and detail pages.
  2. Run collector and parser against fixtures.
  3. Store normalized notice records in a temporary test database.
- Expected result:
  - New records are inserted once.
  - Duplicate URL records are skipped or updated without inflating new counts.
  - Raw source reference is preserved.

### Test: Media opportunity classification

- Steps:
  1. Run classifier against fixtures for website建设、新媒体运营、视频拍摄、信息化建设、GEO 类项目 and unrelated procurement.
  2. Inspect category, evidence and confidence.
- Expected result:
  - Clear media projects are classified into the correct categories.
  - Broad information technology projects without media-relevant subitems are marked as edge opportunities or excluded.
  - GEO examples are tagged separately with conservative confidence if evidence is weak.

### Test: Opportunity scoring

- Steps:
  1. Run scorer against normalized notices with budget, deadline, buyer and risk fields.
  2. Compare generated A/B/C/D class to expected fixture labels.
- Expected result:
  - Strong projects receive A or B only when business fit and evidence are clear.
  - Risk labels lower or qualify the recommendation.
  - Missing fields produce conservative output rather than fabricated values.

### Test: DingTalk brief rendering

- Steps:
  1. Generate a daily brief from a mixed set of A/B/C/D opportunities.
  2. Render to DingTalk message format.
- Expected result:
  - Brief includes top opportunities, reasons, risks and follow-up prompts.
  - Empty-day brief is explicit and useful.
  - Long brief is summarized without losing A-class projects.

### Test: Group Q&A boundary

- Steps:
  1. Ask project-specific questions with exact and fuzzy references.
  2. Ask out-of-scope questions unrelated to procurement intelligence.
- Expected result:
  - Agent answers project questions with conclusion, evidence, risk and next step.
  - Agent asks clarification when multiple projects match.
  - Agent declines or redirects out-of-scope questions.

## OpenClaw Runtime Validation

- Manual runtime test command: blocked until the runtime target and invocation mechanism are confirmed.
- Expected result after runtime setup: Agent is recognized in the OpenClaw runtime, can access its identity files and can answer a bounded procurement intelligence prompt without runtime errors.

Manual checklist until runtime command is confirmed:

- Agent identity is visible and specific to政采情报。
- Agent does not present itself as a generic assistant.
- Agent can explain its non-goals.
- Agent can summarize one fixture opportunity card.
- Agent can refuse an out-of-scope投标执行 request.

## Manual Task Tests

### Test: Daily brief for business staff

- Given: A test database contains three A/B opportunities and five C/D opportunities.
- When: Daily brief generation runs.
- Then: The DingTalk-ready message highlights A/B opportunities first and summarizes C/D items compactly.

### Test: Single notice evaluation

- Given: A notice contains website建设 and新媒体运营 evidence.
- When: User asks whether it is worth following.
- Then: Agent returns opportunity class, evidence, risks and recommended action.

### Test: Broad IT project filter

- Given: A notice contains only hardware、网络设备 or generic系统集成 content.
- When: Classifier runs.
- Then: Project is not promoted to A/B without media-relevant evidence.

### Test: GEO opportunity

- Given: A notice references AI search optimization, answer engine optimization, GEO, large model content discoverability or related terms.
- When: Classifier runs.
- Then: Project is tagged as GEO category with evidence and conservative scoring unless budget and deliverables are clear.

### Test: Out-of-scope group question

- Given: User asks Agent to submit bid documents or register for tender.
- When: Agent responds.
- Then: Agent refuses execution and may provide a high-level checklist only if it is clearly marked as non-executing guidance.

## Regression Checklist

- Project documents are complete enough for another coding agent.
- Artifact type and runtime boundary remain clear.
- No invented OpenClaw commands are present.
- No direct edits to `~/.openclaw/` are required.
- Agent remains scoped to情报发现、项目研判、简报、问答 in first version.
- Assumptions and open questions are separated.
- DingTalk integration does not commit secrets.
- Runtime package excludes `.env`, databases, caches, dependency folders and development docs.
