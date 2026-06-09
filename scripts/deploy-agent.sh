#!/usr/bin/env bash
set -euo pipefail

AGENT_NAME="${AGENT_NAME:-zhejiang-procurement-intel-agent}"
SOURCE_DIR="openclaw/agent"
TARGET_DIR="${OPENCLAW_AGENT_WORKSPACE:-$HOME/.openclaw/workspace-${AGENT_NAME}}"
CONFIRM_DEPLOY="${CONFIRM_DEPLOY:-}"

if [ "$CONFIRM_DEPLOY" != "1" ]; then
  echo "Deployment is disabled by default."
  echo "Run only after delivery audit and explicit user approval:"
  echo "CONFIRM_DEPLOY=1 bash scripts/deploy-agent.sh"
  exit 1
fi

if [ ! -f "${SOURCE_DIR}/AGENTS.md" ]; then
  echo "Missing ${SOURCE_DIR}/AGENTS.md"
  exit 1
fi

echo "Deploying agent workspace to: ${TARGET_DIR}"

if [ -d "${TARGET_DIR}" ] && [ -n "$(ls -A "${TARGET_DIR}" 2>/dev/null)" ]; then
  BACKUP_DIR="${TARGET_DIR}.backup.$(date +%Y%m%d%H%M%S)"
  echo "Existing target found. Creating backup: ${BACKUP_DIR}"
  cp -a "${TARGET_DIR}" "${BACKUP_DIR}"
fi

mkdir -p "${TARGET_DIR}"
rsync -av \
  --exclude ".git/" \
  --exclude ".env" \
  --exclude ".env.*" \
  --exclude "credentials/" \
  --exclude "secrets/" \
  --exclude "node_modules/" \
  --exclude ".venv/" \
  --exclude "venv/" \
  --exclude "__pycache__/" \
  --exclude ".pytest_cache/" \
  "${SOURCE_DIR}/" "${TARGET_DIR}/"

echo "Agent workspace deployed."
echo "Next: run the Manual Runtime Test Command from docs/openclaw-contract.md"
