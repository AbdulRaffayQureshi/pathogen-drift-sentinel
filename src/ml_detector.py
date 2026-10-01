#!/usr/bin/env python3
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

def evaluate_anomalies(df: pd.DataFrame) -> tuple[pd.DataFrame, str, float]:
    df = df.copy()

    # Compute per-target drift relative to each organism's own historical baseline
    df["gc_drift"] = (df["gc_pct"] - df.groupby("target")["gc_pct"].transform("mean")).abs()
    df["entropy_drift"] = (df["kmer_entropy"] - df.groupby("target")["kmer_entropy"].transform("mean")).abs()

    features = ["delta_records", "gc_drift", "entropy_drift"]
    X = df[features].fillna(0.0).values

    if len(df) >= 8:
        model = IsolationForest(n_estimators=150, contamination=0.05, random_state=42)
        model.fit(X)
        raw_scores = model.decision_function(X)

        # Only flag ANOMALY if IsolationForest score < 0 AND the target actually drifted in count or composition
        has_real_shift = (df["delta_records"].abs() >= 10) | (df["gc_drift"] >= 0.5) | (df["entropy_drift"] >= 0.05)
        df["anomaly_flag"] = np.where((raw_scores < 0.0) & has_real_shift, "ANOMALY", "NORMAL")
        df["anomaly_score"] = np.round(np.where(df["anomaly_flag"] == "NORMAL", np.abs(raw_scores) + 0.08, raw_scores), 4)
    else:
        df["anomaly_flag"] = "WARMUP"
        df["anomaly_score"] = 0.1500

    latest_timestamp = df["timestamp"].max()
    latest_slice = df[df["timestamp"] == latest_timestamp]

    min_score = float(latest_slice["anomaly_score"].min())
    has_anomaly = (latest_slice["anomaly_flag"] == "ANOMALY").any()
    overall_state = "ANOMALY_DETECTED" if has_anomaly else ("MODEL_WARMUP" if len(df) < 8 else "NOMINAL")

    return df, overall_state, min_score
