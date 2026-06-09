# AGENTS.md

## Role

You are a coding agent building an OpenClaw-native AI application.

This repository is not the OpenClaw runtime workspace. It is a development repository.

Your job is to update the deployable package under `openclaw/` so it can be safely deployed into OpenClaw.

## Read First

Before making changes, read:

1. `docs/project_spec.md`
2. `docs/openclaw-contract.md`
3. `docs/test_plan.md`
4. Existing files under `openclaw/`

If files conflict, follow this priority:

1. `docs/openclaw-contract.md`
2. `docs/project_spec.md`
3. Existing implementation
4. Your own judgment

## Development Rules

- Do not edit `~/.openclaw/` directly.
- Do not invent OpenClaw CLI commands, flags, subcommands, configuration keys, or file locations.
- Do not use OpenClaw commands that are not explicitly listed in `docs/openclaw-contract.md`.
- Do not manually copy, move, delete, or overwrite files under `~/.openclaw/`.
- Deployment scripts are the only approved way to sync this repository into OpenClaw runtime paths.
- Do not hard-code secrets, API keys, tokens, cookies, SSH keys, or private credentials.
- Do not hard-code machine-specific absolute paths unless explicitly allowed in the contract.
- Keep changes small and reviewable.
- Update `docs/decision_log.md` when making assumptions.
- Update the deployable package under `openclaw/`.
- Run `bash scripts/validate.sh` before finishing.

## Skill Rules

If this project is a Skill:

- The deployable Skill must live under `openclaw/skill/`.
- It must contain `SKILL.md`.
- `SKILL.md` must include YAML frontmatter with `name` and `description`.
- The Skill name must use snake_case.
- The description must clearly say when the Skill should be used.
- Do not put vague personality instructions in the Skill.
- Do not use shell commands built from raw user input.
- Put helper scripts under `openclaw/skill/scripts/`.
- Put static reference material under `openclaw/skill/resources/`.

## Sub-agent Rules

If this project is a sub-agent:

- The deployable agent workspace must live under `openclaw/agent/`.
- It may include `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`, and `skills/`.
- Do not reuse another active agent workspace.
- Do not put secrets into workspace files.
- Do not mix development notes with runtime identity instructions.

## Validation Rules

Validation has three levels.

Level 1: Static validation. Always required.

- Check required files exist.
- Check `SKILL.md` frontmatter is valid if this is a Skill.
- Check required agent workspace files exist if this is a sub-agent.
- Run `bash scripts/validate.sh`.

Level 2: Local functional validation. Required when tests or mock scripts exist.

- Run local tests or mock scripts.
- Include stdout/stderr in the final report.

Level 3: OpenClaw runtime validation. Required only after deployment and only when OpenClaw CLI is available.

- Run the manual runtime test command from `docs/openclaw-contract.md`.
- Do not invent test commands.
- Include stdout/stderr in the final report.
- If runtime validation cannot be performed, state the reason clearly.

## Completion Report

At the end, report:

1. Files changed
2. Commands run
3. Validation result
4. Manual OpenClaw test command
5. Anything not validated
