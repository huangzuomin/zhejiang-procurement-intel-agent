# Release Process

## Purpose

This document defines how the Zhejiang procurement intelligence Agent is versioned, released and deployed. It exists to keep the development repository, GitHub, OpenClaw runtime workspace and runtime schedule aligned.

## Version Layers

The system has three versioned layers:

- Code version: Git commits, pull requests and annotated Git tags.
- Runtime schedule version: the enabled OpenClaw automation schedule and command set.
- Runtime data/schema version: SQLite database schema and operational data retention rules.

Do not treat a deployment as complete unless all three layers are understood.

## Code Versioning

Use semantic versions:

```text
MAJOR.MINOR.PATCH
```

Recommended meanings:

- `MAJOR`: incompatible runtime or data model changes.
- `MINOR`: new capability, new scheduled flow or new durable data table.
- `PATCH`: bug fix, template change or operational hardening without changing the runtime contract.

Current release line:

```text
v0.1.0  Dual-column public collection and daily pipeline MVP
v0.2.0  SQLite hourly collection, DB-backed AM/PM brief, push-event dedupe, health report
v0.2.1  DingTalk Markdown DB brief template refinement
```

Planned release line:

```text
v0.3.0  Award result collection
v0.4.0  Project lifecycle linking
v0.5.0  Buyer and supplier profiles
v1.0.0  Stable production release
```

## Branch and PR Flow

Use this flow for normal development:

```text
feature branch
  -> pull request
  -> validate
  -> controlled smoke if runtime behavior changes
  -> merge main
  -> annotated tag
  -> deploy by tag or approved commit
  -> runtime smoke
  -> deploy log entry
```

Rules:

- Do not deploy an arbitrary dirty worktree.
- Prefer deploying an annotated Git tag.
- An approved commit may be deployed only for an urgent hotfix, and must be tagged afterward.
- Runtime-side fixes must be pushed back to GitHub as a branch and PR.

## Tagging

After a release PR is merged:

```bash
git switch main
git pull --ff-only origin main
git tag -a v0.2.0 -m "SQLite hourly collection and DB brief runtime"
git push origin v0.2.0
```

For a patch release:

```bash
git tag -a v0.2.1 -m "DingTalk Markdown DB brief template refinement"
git push origin v0.2.1
```

## Required Checks Before Tagging

Run:

```bash
bash scripts/validate.sh
python3 scripts/prepare_deploy_dry_run.py --json
```

Required results:

- `validate.sh` passes.
- `forbidden_matches` is `[]`.
- No runtime data, reports, SQLite databases, secrets or credentials are committed.

If the change affects collection, SQLite, scheduling, DingTalk output or deployment, also run a controlled smoke before deployment.

## Runtime Smoke Before Deployment

For the SQLite hourly collection release line:

```bash
python3 scripts/run_hourly_collection.py --today $(date +%F) --hour $(date +%H) --db-path data/procurement_intel.db --limit 5 --detail-limit 5
python3 scripts/run_hourly_collection.py --today $(date +%F) --hour $(date +%H) --db-path data/procurement_intel.db --limit 5 --detail-limit 5
python3 scripts/run_brief_from_db.py --mode am --today $(date +%F) --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/am
python3 scripts/run_brief_from_db.py --mode pm --today $(date +%F) --since-brief am --db-path data/procurement_intel.db --output-dir reports/$(date +%F)/pm
python3 scripts/run_health_report.py --today $(date +%F) --db-path data/procurement_intel.db --output reports/$(date +%F)/health_report.json
```

Only run `--record-push-success` after DingTalk actually accepts the outbound AM message.

Smoke acceptance:

- First hourly run succeeds.
- Second same-day hourly run uses known URLs.
- Known URL detail skip does not degrade stored buyer, budget, deadline or opportunity class.
- AM brief renders.
- PM brief does not repeat successfully pushed AM focus opportunities.
- Health report is `PASS` or an understood `WARN`.

## Deployment Log

Every deployment must append `docs/deploy_log.md`.

Required fields:

- Date and time.
- Git tag or commit.
- Runtime server.
- Runtime path.
- Runtime schedule version.
- Validation result.
- Dry-run result.
- Smoke result.
- Rollback target.
- Operator or deploying agent.

## Rollback

Rollback target should be the last successfully deployed tag or approved commit.

Before rollback:

- Preserve current runtime logs.
- Preserve SQLite database backup if schema changes are involved.
- Record the rollback reason in `docs/deploy_log.md`.

Rollback should restore both code and runtime schedule when the schedule changed.
