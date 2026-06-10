# Deploy Manifest

## Project

政采情报库 Agent

## Artifact Type

OpenClaw sub-agent workspace with internal Skills.

## Development Repository

```text
/home/ai/projects/openclaw-apps/zhejiang-procurement-intel-agent
```

## Runtime Target

Default target for the next approved deployment:

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

This document only records the target. No runtime deployment has been executed.

## Source Package

Primary Agent source:

```text
openclaw/agent/
```

Tool-layer source included by Scheme A:

```text
src/procurement_intel/
scripts/
```

## Packaging Strategy

Recommended scheme: **Scheme A - agent workspace with tool layer**.

Deployable package consists of:

- `openclaw/agent/`
- approved `src/procurement_intel/` files
- approved command wrappers in `scripts/`
- `package.json` for JavaScript collector dependency metadata

Rejected for this release: **Scheme B - docs-only agent plus external support service**. Scheme B would keep tools in the development repository or a separate local service, but service discovery, runtime permissions, lifecycle, and failure handling are not defined yet. Scheme A is simpler, auditable, and lets the Agent runtime carry the deterministic local tool layer it documents.

## Deployment Mode

```text
agent_workspace_sync
```

## Pre-deployment Requirements

- Delivery audit must be PASS, or PASS_WITH_WARNINGS with explicit user approval.
- `bash scripts/validate.sh` must pass.
- Runtime target must be explicitly confirmed by the user before actual deployment.
- Backup must be created before deployment.
- DingTalk secrets must be provided through runtime configuration, not committed files.
- Deployment dry-run must report no forbidden matches.
- Do not deploy reports unless explicitly approved as fixtures.

## Files Allowed to Deploy

From `openclaw/agent/`:

- `AGENTS.md`
- `IDENTITY.md`
- `SOUL.md`
- `USER.md`
- `TOOLS.md`
- `skills/`
- `resources/`

Approved `src/` files:

- `src/procurement_intel/__init__.py`
- `src/procurement_intel/briefing.py`
- `src/procurement_intel/classifier.py`
- `src/procurement_intel/collector.py`
- `src/procurement_intel/daily_pipeline.py`
- `src/procurement_intel/db_briefing.py`
- `src/procurement_intel/external_fetcher.py`
- `src/procurement_intel/health.py`
- `src/procurement_intel/hourly_ingestion.py`
- `src/procurement_intel/models.py`
- `src/procurement_intel/parser.py`
- `src/procurement_intel/qa.py`
- `src/procurement_intel/scorer.py`
- `src/procurement_intel/scrape_quality.py`
- `src/procurement_intel/storage.py`

Approved `scripts/` files:

- `scripts/evaluate_scrape_quality.py`
- `scripts/prepare_deploy_dry_run.py`
- `scripts/query_opportunity_cards.py`
- `scripts/run_brief_from_db.py`
- `scripts/run_daily_pipeline.py`
- `scripts/run_health_report.py`
- `scripts/run_hourly_collection.py`
- `scripts/run_hourly_ingest.py`
- `scripts/validate.sh`
- `scripts/zfcg_browser_scraper.js`

Approved root dependency manifest:

- `package.json`

## Files Never Deploy

- `.git/`
- `.env`
- `.env.*`
- `credentials/`
- `secrets/`
- `*.pem`
- `*.key`
- `node_modules/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `*.log`
- `docs/`
- `tests/`
- `reports/` unless explicitly approved as fixtures
- `references/`
- `handoff/`
- `data/govproc.db`
- Any local runtime database unless explicitly approved.
- Any DingTalk token, webhook URL, app secret or credential file.

## Deployment Dry-run Check

Run before real deployment:

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```

Required dry-run properties:

- `runtime_target`: `~/.openclaw/workspace-zhejiang-procurement-intel-agent`
- `packaging_strategy`: `agent_workspace_with_tool_layer`
- `recommended_scheme`: `A`
- `forbidden_matches`: `[]`

This command must not copy, delete, or modify runtime files.

## Runtime Invocation Entrypoints

Run one hourly public collection into SQLite:

```bash
python3 scripts/run_hourly_collection.py --today <date> --hour <HH> --db-path data/procurement_intel.db
```

Generate the AM brief from SQLite:

```bash
python3 scripts/run_brief_from_db.py --mode am --today <date> --db-path data/procurement_intel.db --output-dir reports/<date>/am
```

Generate the PM incremental brief from SQLite:

```bash
python3 scripts/run_brief_from_db.py --mode pm --today <date> --since-brief am --db-path data/procurement_intel.db --output-dir reports/<date>/pm
```

Generate collection health report:

```bash
python3 scripts/run_health_report.py --today <date> --db-path data/procurement_intel.db --output reports/<date>/health_report.json
```

Generate a brief from an existing scraper JSON:

```bash
python3 scripts/run_daily_pipeline.py <zfcg-json> --today <date> --output-dir <output-dir>
```

Answer questions from opportunity cards:

```bash
python3 scripts/query_opportunity_cards.py <opportunity_cards.json> "<question>"
```

## Backup Rule

Before deployment, create a timestamped backup:

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent.backup.YYYYMMDD-HHMMSS
```

## Deployment Strategy

Conservative sync by default:

- Copy approved files only.
- Skip forbidden files.
- Do not delete target files unless explicitly approved.
- Do not deploy until the user approves runtime target and Scheme A packaging.

## Post-deployment Validation

Manual OpenClaw runtime invocation is still pending. Local command entrypoints are documented above.

Do not invent OpenClaw CLI commands.

Manual validation expectations:

- Agent identity loads as政采情报库 Agent.
- Agent can state first-version scope.
- Agent can generate or explain a daily procurement opportunity brief.
- Agent can answer from `opportunity_cards.json`.
- Agent can refuse投标执行 requests.
- DingTalk outbound test uses non-secret runtime configuration.

## Rollback

If deployment fails, restore from the backup created during this deployment.

## Deployment Record

Append deployment result to:

```text
docs/deploy_log.md
```
