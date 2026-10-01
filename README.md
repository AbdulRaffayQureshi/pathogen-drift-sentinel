# Pathogen & Genomic Drift Sentinel (v2.0 MLOps)

Automated Linux/Zsh Bioinformatics & Unsupervised Anomaly Detection pipeline executing every 5 hours via GitHub Actions, DuckDB/Parquet OLAP storage, and Scikit-learn `IsolationForest`.

![Live Genomic Surveillance Dashboard](assets/telemetry_dashboard.svg)

## Live Genomic & ML Telemetry
* **Last Automated Sync (UTC):** `2026-10-01 21:40:31 UTC`
* **Total DuckDB Parquet Snapshots:** `8`
* **Macro Distribution Entropy ($H$):** `0.2747 bits`
* **Isolation Forest Status:** `NOMINAL` (Min Decision Score: `0.0000`)

| Surveillance Target | NCBI Records | 5h Velocity ($\Delta$) | FASTA GC% | 3-mer Complexity ($H_3$) | Isolation Forest State |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `H5N1_Avian_Flu` | 229,067 | `+0` | 45.17% | 5.8697 bits | 🟢 NORMAL (`0.198`) |
| `blaNDM_AMR_Gene` | 10,315 | `+0` | 0.00% | 0.0000 bits | 🟢 NORMAL (`0.000`) |
| `SLC6A4_Variants` | 36 | `+0` | 50.47% | 5.8743 bits | 🟢 NORMAL (`0.181`) |
| `A_baumannii_Meropenem` | 373 | `+0` | 46.82% | 5.8287 bits | 🟢 NORMAL (`0.177`) |

---
*Backed by DuckDB ZSTD Parquet storage & Scikit-learn Isolation Forest • Automated via GitHub Actions.*
