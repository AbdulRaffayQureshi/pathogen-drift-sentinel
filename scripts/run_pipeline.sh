#!/usr/bin/env bash
set -uo pipefail
if [[ -f .env ]]; then source .env; fi

START_TIME=$(date +%s)
rm -f /tmp/sentinel_status.env

echo "[INFO] Starting Pathogen Drift Sentinel v2.0 MLOps pipeline..."
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
    ML_STATE="CRASHED"
    ML_SCORE="0.0000"
    ERROR_MESSAGE="Python process terminated before writing status file."
fi

if [[ -n "${GITHUB_RUN_ID:-}" ]]; then
    RUN_LINK="[View Run #${GITHUB_RUN_ID}](${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})"
else
    RUN_LINK="Local WSL Zsh Execution"
fi

if [[ -n "${DISCORD_WEBHOOK_URL:-}" ]]; then
    if [[ $EXIT_CODE -ne 0 ]]; then
        COLOR=15158332 # Red
        TITLE="🚨 Bio-Sentinel v2.0 Failed (Errors Detected)"
    elif [[ "${ML_STATE}" == "ANOMALY_DETECTED" ]]; then
        COLOR=16753920 # Amber Warning
        TITLE="⚠️ Bio-Sentinel v2.0: Genomic Drift Anomaly Flagged"
    else
        COLOR=3066993 # Green
        TITLE="✅ Bio-Sentinel v2.0 Executed (No Errors)"
    fi

    PAYLOAD=$(cat <<JSON
{
  "username": "Sentinel MLOps Bot",
  "embeds": [{
    "title": "${TITLE}",
    "color": ${COLOR},
    "fields": [
      {"name": "Status", "value": "\`${PIPELINE_STATUS}\`", "inline": true},
      {"name": "Targets Synced", "value": "\`${RECORDS_PROCESSED}\`", "inline": true},
      {"name": "Macro Entropy", "value": "\`${DRIFT_ENTROPY} bits\`", "inline": true},
      {"name": "Isolation Forest", "value": "\`${ML_STATE} (${ML_SCORE})\`", "inline": true},
      {"name": "Latency", "value": "\`${DURATION}s\`", "inline": true},
      {"name": "Run Details", "value": "${RUN_LINK}", "inline": true},
      {"name": "Error Diagnostics", "value": "\`${ERROR_MESSAGE}\`", "inline": false}
    ],
    "footer": {"text": "DuckDB Parquet + Scikit-Learn IsolationForest • GitHub Actions"}
  }]
}
JSON
)
    curl -s -H "Content-Type: application/json" -X POST -d "${PAYLOAD}" "${DISCORD_WEBHOOK_URL}" > /dev/null
    echo "[INFO] Discord v2.0 notification dispatched."
fi

exit $EXIT_CODE
