# OpenClaw Contract: 政采情报库 Agent

## Artifact Type

OpenClaw sub-agent workspace with internal Skills.

The Agent is the primary artifact. The supporting application code is a tool layer used by the Agent and must not be treated as the OpenClaw runtime identity.

## Development Repository Boundary

Development happens in this project repository:

```text
/home/ai/projects/openclaw-apps/zhejiang-procurement-intel-agent
```

Do not directly edit the OpenClaw runtime workspace during development.

## Runtime Boundary

The runtime artifact is the approved contents of `openclaw/agent/` plus any explicitly approved support files required by its tools.

Runtime data, local databases, test fixtures, development docs, dependency caches and virtual environments are outside the runtime artifact unless explicitly approved in the deployment manifest.

## Source Paths

```text
openclaw/agent/
src/
scripts/
tests/
scripts/validate.sh
```

`openclaw/agent/` is the source package for the OpenClaw Agent identity and internal Skills.

`src/` contains local Python tool-layer implementation for parsing, classification, scoring, briefing, QA and pipeline orchestration.

`scripts/` contains documented command wrappers for browser collection, daily pipeline execution, quality evaluation, validation and deployment preparation.

`tests/` and fixtures validate behavior but are not deployed by default.

## Runtime Target Paths

Proposed runtime target:

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

This path must be confirmed before deployment.

## Allowed File Changes

- Add or update `docs/` project documents.
- Add or update `openclaw/agent/` files.
- Add or update `src/` implementation files.
- Add or update documented `scripts/` wrappers.
- Add or update `tests/` fixtures and tests.
- Add or update `scripts/validate.sh`.
- Add or update dependency manifests required by the app tool layer.

## Forbidden File Changes

- Do not directly edit `~/.openclaw/`.
- Do not manually copy files into `~/.openclaw/`.
- Do not modify `.venv/`, `venv/`, `node_modules/`, or `__pycache__/`.
- Do not deploy `data/govproc.db` or any local runtime database unless explicitly approved.
- Do not add real DingTalk secrets, webhook URLs, credentials or tokens to the repository.

## Allowed Commands

```bash
bash scripts/validate.sh
git status
git diff
```

Other local development commands may be added to `scripts/validate.sh` during implementation, but the OpenClaw deployment process must not rely on invented OpenClaw CLI commands.

## Forbidden Commands and Actions

- Do not invent OpenClaw CLI commands.
- Do not deploy unless explicitly requested.
- Do not claim validation passed unless the exact command was run.
- Do not bypass login, CAPTCHA, access controls or robots-style restrictions.
- Do not scrape non-public procurement data.
- Do not let the Agent execute投标报名、投标文件提交、付款或合同类动作。

## Validation Requirements

Before implementation is considered complete:

- `bash scripts/validate.sh` must run and pass.
- Static validation must ensure required Agent files exist.
- Tests must cover opportunity classification, scoring, brief generation and bounded Q&A.
- Validation must detect forbidden runtime files in deployable packages.

## Manual Runtime Test Command

Manual OpenClaw runtime test command is not confirmed. Use a documented manual checklist until the runtime target and invocation mechanism are confirmed.

## Open Questions

- Final runtime target path.
- DingTalk inbound message mechanism and outbound robot configuration.
- Whether `src/` and `scripts/` tool-layer code are deployed with the Agent workspace or exposed through a separate local service.
- Exact schedule for daily and weekly briefs.
