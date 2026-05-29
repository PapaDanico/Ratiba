#!/bin/bash
# SessionStart hook: bring up the Ratiba demo stack so the app is reachable and
# tests/linters can run. Web (Claude Code on the web) only — local machines run
# their own stack. Idempotent; see scripts/dev-up.sh.
set -uo pipefail

# Only run in the remote (web) environment.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

bash "${CLAUDE_PROJECT_DIR:-.}/scripts/dev-up.sh" >> /tmp/ratiba-sessionstart.log 2>&1 || true
