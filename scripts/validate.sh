#!/usr/bin/env bash
set -euo pipefail

echo "Validating OpenClaw project..."

PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ ! -f "AGENTS.md" ]; then
  echo "Missing AGENTS.md"
  exit 1
fi

if [ ! -f "docs/project_spec.md" ]; then
  echo "Missing docs/project_spec.md"
  exit 1
fi

if [ ! -f "docs/openclaw-contract.md" ]; then
  echo "Missing docs/openclaw-contract.md"
  exit 1
fi

if [ -f "openclaw/skill/SKILL.md" ]; then
  echo "Checking Skill package..."

  if ! grep -q "^---" openclaw/skill/SKILL.md; then
    echo "SKILL.md missing YAML frontmatter delimiter"
    exit 1
  fi

  if ! grep -q "^name:" openclaw/skill/SKILL.md; then
    echo "SKILL.md missing name field"
    exit 1
  fi

  if ! grep -q "^description:" openclaw/skill/SKILL.md; then
    echo "SKILL.md missing description field"
    exit 1
  fi
fi

if [ -d "openclaw/agent" ]; then
  echo "Checking agent workspace package..."

  for f in AGENTS.md SOUL.md IDENTITY.md USER.md TOOLS.md; do
    if [ ! -f "openclaw/agent/$f" ]; then
      echo "Missing openclaw/agent/$f"
      exit 1
    fi
  done

  for d in skills/daily_procurement_brief skills/notice_opportunity_eval skills/procurement_qa skills/keyword_strategy_tuning resources; do
    if [ ! -e "openclaw/agent/$d" ]; then
      echo "Missing openclaw/agent/$d"
      exit 1
    fi
  done

  if [ -e "openclaw/agent/skills/example_skill" ]; then
    echo "Placeholder example_skill must be removed"
    exit 1
  fi
fi

if grep -R "replace_with_" AGENTS.md README.md docs openclaw 2>/dev/null; then
  echo "Unresolved template placeholder found"
  exit 1
fi

if find tests -name "test_*.py" -print -quit | grep -q .; then
  echo "Running Python tests..."
  PYTHONPATH=src "$PYTHON_BIN" -m pytest tests -v
fi

echo "Validation passed."
