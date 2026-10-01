#!/usr/bin/env bash
set -uo pipefail
if [[ -f .env ]]; then source .env; fi

START_TIME=$(date +%s)
rm -f /tmp/sentinel_status.env

echo "[INFO] Starting Pathogen Drift Sentinel pipeline..."
python3 src/sentinel.py
EXIT_CODE=$?

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [[ -f /tmp/sentinel_status.env ]]; then
    source /tmp/sentinel_status.env
else
    PIPELINE_STATUS="CRITICAL_FAILURE"
    RECORDS_PROCESSED="0"
    DRIFT_ENTROPY="0.0000"
    ERROR_MESSAGE="Python process terminated before writing status file."
fi

if [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    RUN_LINK="[View Run #${GITHUB_RUN_ID}](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})"
else
    RUN_LINK="Local WSL Zsh Execution"
fi

if [[ -n "${DISCORD_WEBHOOK_URL:-}" ]]; then
    if [[ $EXIT_CODE -eq 0 ]]; then
        COLOR=3066993
        TITLE="✅ Bio-Sentinel Pipeline Executed (No Errors)"
    else
        COLOR=15158332
        TITLE="🚨 Bio-Sentinel Pipeline Failed (Errors Detected)"
    fi

    PAYLOAD=$(cat <<JSON
{
  "username": "Sentinel MLOps Bot",
  "embeds": [{
    "title": "${TITLE}",
    "color": ${COLOR},
    "fields": [
      {"name": "Status", "value": "\`${PIPELINE_STATUS}\`", "inline": true},
      {"name": "Targets Processed", "value": "\`${RECORDS_PROCESSED}\`", "inline": true},
      {"name": "Shannon Entropy", "value": "\`${DRIFT_ENTROPY} bits\`", "inline": true},
      {"name": "Execution Time", "value": "\`${DURATION}s\`", "inline": true},
      {"name": "Run Details", "value": "${RUN_LINK}", "inline": true},
      {"name": "Error Diagnostics", "value": "\`${ERROR_MESSAGE}\`", "inline": false}
    ],
    "footer": {"text": "GitHub Actions Automated Cron • WSL Zsh Pipeline"}
  }]
}
JSON
)
    curl -s -H "Content-Type: application/json" -X POST -d "${PAYLOAD}" "${DISCORD_WEBHOOK_URL}" > /dev/null
    echo "[INFO] Discord notification dispatched."
else
    echo "[WARN] DISCORD_WEBHOOK_URL not set; skipping Discord webhook."
fi

exit $EXIT_CODE
