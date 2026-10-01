#!/usr/bin/env python3
import json 
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "telemetry_history.json"
README_FILE = BASE_DIR / "README.md"
STATUS_ENV = Path("/tmp/sentinel_status.env")

TARGETS = {
    "A_baumannii_Meropenem": '"Acinetobacter baumannii"[Organism] AND meropenem[All Fields]',
    "blaNDM_AMR_Gene": 'blaNDM[All Fields] AND "antimicrobial resistance"[All Fields]',
    "H5N1_Avian_Flu": '"Influenza A virus"[Organism] AND H5N1[All Fields]',
    "SLC6A4_Variants": 'SLC6A4[Gene Name] AND "Homo sapiens"[Organism]'
}


NCBI_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

def write_status(status: str, processed: int, entropy: float, error_msg: str = "None"):
    clean_err = error_msg.replace('"', "'").replace("\n", " ")[:180]
    with open(STATUS_ENV, "w", encoding="utf-8") as f:
        f.write(f'PIPELINE_STATUS="{status}"\n')
        f.write(f'RECORDS_PROCESSED="{processed}"\n')
        f.write(f'DRIFT_ENTROPY="{entropy:.4f}"\n')
        f.write(f'ERROR_MESSAGE="{clean_err}"\n')

def fetch_ncbi_count(query: str) -> int:
    params = {
        "db": "nuccore",
        "term": query,
        "retmode": "json",
        "retmax": 0
    }
    headers = {"User-Agent": "PathogenDriftSentinel/1.0 (Linux-WSL-Automation)"}
    resp = requests.get(NCBI_ESEARCH_URL, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return int(data["esearchresult"]["count"])

def compute_shannon_entropy(counts: list[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)
    return round(entropy, 4)

def update_readme(timestamp: str, metrics: dict, entropy: float, total_runs: int):
    rows = "\n".join(
        [f"| `{target}` | {count:,} | {round((count / max(sum(metrics.values()), 1)) * 100, 2)}% |"
         for target, count in metrics.items()]
    )
    content = f"""# Pathogen & Genomic Drift Sentinel

Automated Linux/Zsh MLOps & Bioinformatics telemetry pipeline executing every 5 hours via GitHub Actions.

## Live Genomic Surveillance Telemetry
* **Last Automated Sync (UTC):** `{timestamp}`
* **Cumulative Pipeline Executions:** `{total_runs}`
* **Shannon Distribution Entropy ($H$):** `{entropy:.4f} bits`

| Surveillance Target | Indexed Nucleotide Records (NCBI) | Relative Share |
| :--- | :---: | :---: |
{rows}

---
*Updated automatically by `pathogen-drift-sentinel` CI/CD daemon.*
"""
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    metrics = {}
    try:
        for name, query in TARGETS.items():
            metrics[name] = fetch_ncbi_count(query)
            time.sleep(0.4)  # Respect NCBI rate limit (3 req/sec without API key)

        entropy = compute_shannon_entropy(list(metrics.values()))

        history = []
        if DATA_FILE.exists():
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = []

        snapshot = {
            "timestamp": timestamp,
            "entropy_bits": entropy,
            "counts": metrics
        }
        history.append(snapshot)
        history = history[-500:]  # Retain rolling window of last 500 runs

        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        update_readme(timestamp, metrics, entropy, len(history))
        write_status("SUCCESS", len(metrics), entropy, "No errors detected")
        print(f"[OK] Synced {len(metrics)} targets | Entropy: {entropy:.4f} bits")

    except Exception as exc:
        write_status("ERROR", len(metrics), 0.0, str(exc))
        print(f"[FATAL] Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
