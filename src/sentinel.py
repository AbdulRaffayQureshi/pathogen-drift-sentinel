#!/usr/bin/env python3
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import sys
import time

from bio_features import fetch_target_bio_features
from storage_duckdb import append_and_query_telemetry
from ml_detector import evaluate_anomalies
from visualizer import render_dashboard

BASE_DIR = Path(__file__).resolve().parent.parent
README_FILE = BASE_DIR / "README.md"
STATUS_ENV = Path("/tmp/sentinel_status.env")

TARGETS = {
    "A_baumannii_Meropenem": '"Acinetobacter baumannii"[Organism] AND meropenem[All Fields]',
    "blaNDM_AMR_Gene": 'blaNDM[All Fields] AND "antimicrobial resistance"[All Fields] AND 200:5000[SLEN]',
    "H5N1_Avian_Flu": '"Influenza A virus"[Organism] AND H5N1[All Fields]',
    "SLC6A4_Variants": 'SLC6A4[Gene Name] AND "Homo sapiens"[All Fields]'
}

def write_status(status: str, processed: int, entropy: float, ml_state: str, ml_score: float, error_msg: str = "No errors detected"):
    clean_err = error_msg.replace("\\", "/").replace('"', "'").replace("\n", " ")[:180]
    with open(STATUS_ENV, "w", encoding="utf-8") as f:
        f.write(f'PIPELINE_STATUS="{status}"\n')
        f.write(f'RECORDS_PROCESSED="{processed}"\n')
        f.write(f'DRIFT_ENTROPY="{entropy:.4f}"\n')
        f.write(f'ML_STATE="{ml_state}"\n')
        f.write(f'ML_SCORE="{ml_score:.4f}"\n')
        f.write(f'ERROR_MESSAGE="{clean_err}"\n')

def compute_macro_entropy(counts: list[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    return round(-sum((c / total) * math.log2(c / total) for c in counts if c > 0), 4)

def update_readme(latest_df, total_snapshots: int, macro_entropy: float, ml_state: str, ml_score: float):
    ts = latest_df["timestamp"].iloc[0]
    rows = []
    for _, r in latest_df.iterrows():
        delta_str = f"+{int(r['delta_records'])}" if r["delta_records"] >= 0 else str(int(r["delta_records"]))
        badge = "🔴 ANOMALY" if r["anomaly_flag"] == "ANOMALY" else ("🟡 WARMUP" if r["anomaly_flag"] == "WARMUP" else "🟢 NORMAL")
        rows.append(
            f"| `{r['target']}` | **{int(r['count']):,}** | `{delta_str}` | `{r['gc_pct']:.2f}%` | `{r['kmer_entropy']:.4f} bits` | {badge} (`{r['anomaly_score']:.3f}`) |"
        )
    table_body = "\n".join(rows)

    telemetry_block = f"""<!-- TELEMETRY_START -->
### 📡 Live Genomic & Unsupervised ML Telemetry
* 🕒 **Last Automated Sync (UTC):** `{ts}`
* 🗄️ **Cumulative DuckDB Parquet Snapshots:** `{total_snapshots}`
* 🧬 **Macro Distribution Entropy ($H$):** `{macro_entropy:.4f} bits`
* 🧠 **Isolation Forest Anomaly Engine:** `{ml_state}` *(Min Decision Score: `{ml_score:.4f}`)*

![Live Genomic Surveillance Dashboard](assets/telemetry_dashboard.svg)

| 🎯 Surveillance Target | 🧬 NCBI Records | ⚡ 5h Velocity ($\Delta$) | 🧪 FASTA GC% | 🔢 3-mer Complexity ($H_3$) | 🛡️ Isolation Forest State |
| :--- | :---: | :---: | :---: | :---: | :---: |
{table_body}
<!-- TELEMETRY_END -->"""

    if README_FILE.exists():
        current_text = README_FILE.read_text(encoding="utf-8")
        pattern = re.compile(r"<!-- TELEMETRY_START -->.*?<!-- TELEMETRY_END -->", re.DOTALL)
        if pattern.search(current_text):
            updated_text = pattern.sub(lambda _: telemetry_block, current_text)
            README_FILE.write_text(updated_text, encoding="utf-8")
            return

    # Fallback if markers are missing
    README_FILE.write_text(f"# 🧬 Pathogen & Genomic Drift Sentinel\n\n{telemetry_block}\n", encoding="utf-8")

def main():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    new_rows = []
    try:
        for name, query in TARGETS.items():
            feats = fetch_target_bio_features(query)
            new_rows.append({
                "timestamp": timestamp,
                "target": name,
                "count": feats["count"],
                "gc_pct": feats["gc_pct"],
                "kmer_entropy": feats["kmer_entropy"]
            })
            time.sleep(0.4)

        macro_entropy = compute_macro_entropy([r["count"] for r in new_rows])
        full_df = append_and_query_telemetry(new_rows)
        scored_df, ml_state, ml_score = evaluate_anomalies(full_df)

        render_dashboard(scored_df)
        latest_df = scored_df[scored_df["timestamp"] == timestamp]
        update_readme(latest_df, len(scored_df), macro_entropy, ml_state, ml_score)

        write_status("SUCCESS", len(new_rows), macro_entropy, ml_state, ml_score)
        print(f"[OK] v2.1 Synced | Entropy: {macro_entropy:.4f} | ML State: {ml_state} ({ml_score:.4f})")

    except Exception as exc:
        write_status("ERROR", len(new_rows), 0.0, "FAILED", 0.0, str(exc))
        print(f"[FATAL] Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
