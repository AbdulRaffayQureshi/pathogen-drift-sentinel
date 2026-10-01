#!/usr/bin/env python3
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

def evaluate_anomalies(df: pd.DataFrame) -> tuple[pd.DataFrame, str, float]:
    df = df.copy()
    features = ["delta_records", "gc_pct", "kmer_entropy"]
    X = df[features].fillna(0.0).values

    if len(df) >= 8:
        model = IsolationForest(n_estimators=150, contamination=0.08, random_state=42)
        preds = model.fit_predict(X)
        scores = model.decision_function(X)
        df["anomaly_flag"] = np.where(preds == -1, "ANOMALY", "NORMAL")
        df["anomaly_score"] = np.round(scores, 4)
    else:
        # Bootstrap regime until 2+ cron cycles accumulate >= 8 rows
        df["anomaly_flag"] = "WARMUP"
        df["anomaly_score"] = 0.1500

    latest_timestamp = df["timestamp"].max()
    latest_slice = df[df["timestamp"] == latest_timestamp]

    min_score = float(latest_slice["anomaly_score"].min())
    has_anomaly = (latest_slice["anomaly_flag"] == "ANOMALY").any()
    overall_state = "ANOMALY_DETECTED" if has_anomaly else ("MODEL_WARMUP" if len(df) < 8 else "NOMINAL")

    return df, overall_state, min_score
