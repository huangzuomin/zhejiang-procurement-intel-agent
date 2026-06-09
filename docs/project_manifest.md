# Project Manifest

## Project Name

zhejiang-procurement-intel-agent

## Artifact Type

OpenClaw sub-agent workspace with internal Skills.

## Created From Template

Yes.

## Template Path

```text
/home/ai/projects/openclaw-apps/openclaw-app-template
```

## Project Path

```text
/home/ai/projects/openclaw-apps/zhejiang-procurement-intel-agent
```

## Runtime Target

```text
~/.openclaw/workspace-zhejiang-procurement-intel-agent
```

## Skill Name

Not applicable. This is an agent-first project.

## Agent Name

```text
zhejiang-procurement-intel-agent
```

## Key Files

- `docs/project_spec.md`
- `docs/openclaw-contract.md`
- `docs/test_plan.md`
- `docs/decision_log.md`
- `docs/deploy_manifest.md`
- `openclaw/agent/AGENTS.md`
- `openclaw/agent/IDENTITY.md`
- `openclaw/agent/SOUL.md`
- `openclaw/agent/TOOLS.md`
- `openclaw/agent/USER.md`
- `references/legacy-system/`
- `handoff/zhejiang-procurement-intel-migration-bundle.tar.gz`

## Validation Command

```bash
bash scripts/validate.sh
```

## Deployment Command

```bash
CONFIRM_DEPLOY=1 bash scripts/deploy-agent.sh
```

Deployment is documented only. Do not deploy until delivery audit passes and the user explicitly requests deployment.

## Manual Runtime Test Command

Blocked until runtime target and invocation mechanism are confirmed.

## Initialization Notes

The legacy prototype was not copied wholesale. Only selected reference files were migrated under `references/legacy-system/`; runtime data, dependency folders, virtual environments and caches were excluded.
