# Release Management Rules

## Core Rule

The Agent runtime must not treat "latest files on disk" as a release. A release is an approved Git tag or an explicitly approved commit, paired with a documented runtime schedule version.

## Version Layers

- Code version: Git tag or approved commit.
- Runtime schedule version: documented schedule command set.
- Data/schema version: SQLite schema and runtime data handling.

All three layers must be considered before deployment, rollback or schedule changes.

## Current Release Line

```text
v0.1.0  Dual-column public collection and daily pipeline MVP
v0.2.0  SQLite hourly collection, DB-backed AM/PM brief, push-event dedupe, health report
v0.2.1  DingTalk Markdown DB brief template refinement
```

## Deployment Rules

- Prefer deploying an annotated Git tag.
- Deploy an untagged commit only with explicit user approval.
- Never deploy a dirty runtime worktree.
- Never deploy runtime data, reports, SQLite databases, tokens, cookies or secrets.
- Runtime-side fixes must be pushed back to GitHub as a branch and PR.
- Every deployment or rollback must be recorded in `docs/deploy_log.md` in the development repository.

## Schedule Rules

Current schedule version:

```text
schedule-v0.2.0
```

The SQLite schedule is:

- Hourly collection during business hours.
- AM brief from SQLite.
- Record AM push success only after DingTalk accepts the AM message.
- PM brief from SQLite with AM push dedupe.
- End-of-day health report.

AM/PM brief generation must not launch browser collection.

Do not use `--include-historical` in production hourly schedules.

## Required Checks

Before a release or deployment:

```bash
bash scripts/validate.sh
python3 scripts/prepare_deploy_dry_run.py --json
```

Required:

- Validation passes.
- `forbidden_matches` is `[]`.

For runtime-affecting changes, run a small real smoke:

- Hourly collection with `limit/detail-limit` set to 5 or 10.
- Same-day second hourly collection.
- Confirm known URLs do not degrade stored fields or opportunity classes.
- Generate AM brief.
- Record AM push success only after real DingTalk success.
- Generate PM brief and confirm AM focus items are not repeated.
- Generate health report.

## Rollback Rules

- Roll back to the last successfully deployed tag or approved commit.
- Preserve logs, snapshots and SQLite backup before rollback.
- If the schedule changed, restore the previous schedule too.
- Record the rollback in `docs/deploy_log.md`.
