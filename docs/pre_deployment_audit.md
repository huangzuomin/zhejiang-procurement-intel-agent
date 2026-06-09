# Pre-deployment Audit

## Overall Result

PASS_WITH_WARNINGS

## Gate Result

PASS

## Quality Result

PASS

## Runtime Readiness Result

PASS_WITH_WARNINGS

## Continuity Result

PASS

## Summary

The repository is ready for a user-approved deployment dry run. Runtime deployment was not executed. The runtime target, packaging strategy, deployable file list, forbidden file list, and local runtime entrypoints are now documented.

Remaining warnings are limited to post-deployment runtime invocation details and DingTalk runtime configuration. These are not code-quality blockers but must be resolved before claiming OpenClaw runtime validation.

## Checked Repository

```text
/home/ai/projects/openclaw-apps/zhejiang-procurement-intel-agent
```

## Artifact Type

OpenClaw sub-agent workspace with internal skills.

## Runtime Target

Default target for the next approved deployment:

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

This audit only records the target. No runtime deployment has been executed.

## Packaging Strategy

Recommended and documented scheme: **Scheme A - agent workspace with tool layer**.

Deployable package:

- `openclaw/agent/`
- `src/procurement_intel/`
- approved command wrappers in `scripts/`

Scheme B, a docs-only Agent that calls the development repository or an external local support service, is not recommended for this release because service discovery, permissions, lifecycle, and failure handling are not defined.

## Deployment Mode

```text
agent_workspace_sync
```

## Validation Command

```bash
bash scripts/validate.sh
```

Latest result:

```text
44 passed
Validation passed.
```

## Deployment Dry-run Command

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```

Latest dry-run result:

- `runtime_target`: `~/.openclaw/workspace-zhejiang-procurement-intel-agent`
- `packaging_strategy`: `agent_workspace_with_tool_layer`
- `recommended_scheme`: `A`
- `forbidden_matches`: `[]`

The dry-run command does not copy, delete, or modify runtime files.

## Runtime Invocation Entrypoints

Generate today's brief from live public collection:

```bash
node scripts/zfcg_browser_scraper.js --targets intention,bid --limit 30 --detail-limit 30 --output reports/<date>/zfcg-browser-two-columns-30.json
python3 scripts/run_daily_pipeline.py reports/<date>/zfcg-browser-two-columns-30.json --today <date> --output-dir reports/<date>/daily-pipeline
```

Generate a brief from an existing scraper JSON:

```bash
python3 scripts/run_daily_pipeline.py <zfcg-json> --today <date> --output-dir <output-dir>
```

Answer questions from opportunity cards:

```bash
python3 scripts/query_opportunity_cards.py <opportunity_cards.json> "<question>"
```

## Gate Audit

### Passed

- Required repository docs exist: `AGENTS.md`, `docs/project_spec.md`, `docs/openclaw-contract.md`, `docs/test_plan.md`, `docs/decision_log.md`, `docs/deploy_manifest.md`.
- Required Agent files exist: `openclaw/agent/AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md`.
- Internal Agent skills exist and document daily brief, opportunity evaluation, QA, and keyword tuning.
- `openclaw/skill/SKILL.md` is absent, avoiding agent-only / skill confusion.
- Runtime target is documented.
- Scheme A packaging is documented.
- Dry-run file manifest exists and reports no forbidden matches.
- `scripts/deploy-agent.sh` requires explicit `CONFIRM_DEPLOY=1` and does not use `rsync --delete`.

### Warnings

- Actual runtime deployment has not been executed.
- Manual OpenClaw runtime invocation command is still not confirmed; do not invent one.
- DingTalk inbound/outbound configuration remains pending and must use runtime-provided secrets only.

### Failed

None.

## Security Audit

Result: PASS

No real DingTalk webhook, token, app secret, private key, `.env`, `credentials/`, or `secrets/` file was found in the deployable scope. Dependency and cache directories are excluded by policy and dry-run matching.

## Quality Assessment

### Product Fit

Result: PASS

The Agent has a concrete user, trigger scenario, monitoring scope, output artifacts, and non-goal boundary.

### Artifact Design Quality

Result: PASS

The Agent identity and internal skills are narrow and operational. Skills document inputs, defaults, outputs, acceptance sample, and safety rules.

### Implementation Quality

Result: PASS

The tool layer is organized into collector, parser, classifier, scorer, briefing, QA, quality evaluation, and daily pipeline modules. Side effects are controlled through explicit scripts.

### Test Quality

Result: PASS

Tests cover classification, scoring, scraping adaptation, detail parsing, quality evaluation, dual-column pipeline, real 60-notice acceptance sample, QA from `opportunity_cards.json`, and deployment dry-run manifest.

### User Experience Quality

Result: PASS

The documented entrypoints generate named artifacts and stable brief sections. QA can answer A/B opportunities, project reasoning, and immediate-response bid questions.

## Runtime Readiness

Result: PASS_WITH_WARNINGS

Runtime target and packaging strategy are documented, but actual OpenClaw runtime invocation is still pending. No runtime deployment has been performed.

## Maintainability / Handoff

Result: PASS

`docs/project_manifest.md`, `docs/decision_log.md`, `docs/deploy_manifest.md`, and this audit capture the current state, open questions, and next deployment gate.

## Deployable File Checklist

Generate current list with:

```bash
python3 scripts/prepare_deploy_dry_run.py --json
```

Expected deployable groups:

- `openclaw/agent/`
- `src/procurement_intel/`
- root dependency manifest:
  - `package.json`
- approved scripts:
  - `scripts/evaluate_scrape_quality.py`
  - `scripts/prepare_deploy_dry_run.py`
  - `scripts/query_opportunity_cards.py`
  - `scripts/run_daily_pipeline.py`
  - `scripts/validate.sh`
  - `scripts/zfcg_browser_scraper.js`

## Never Deploy

- `.git/`
- `.env*`
- `credentials/`
- `secrets/`
- `*.pem`
- `*.key`
- `node_modules/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- development-only `docs/`
- test-only `tests/`
- `reports/` unless explicitly approved as fixtures
- `references/`
- `handoff/`

## Next Gate

Before real deployment, confirm:

1. Proceed with target `~/.openclaw/workspace-zhejiang-procurement-intel-agent`.
2. Proceed with Scheme A packaging.
3. Whether acceptance sample reports should be copied, regenerated, or excluded.
4. Runtime method for invoking the documented local entrypoints.
5. DingTalk secret/config source.
