#!/usr/bin/env python3
import sys
from pathlib import Path
import pandas as pd
import pytest

# Add src/ to Python path so pytest can import pipeline modules directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from bio_features import compute_gc_content, compute_kmer_entropy
from ml_detector import evaluate_anomalies

def test_gc_content_calculation():
    assert compute_gc_content("GGCCGGCC") == 100.0
    assert compute_gc_content("AATTAATT") == 0.0
    assert compute_gc_content("ATGCATGC") == 50.0
    assert compute_gc_content("") == 0.0

def test_kmer_shannon_entropy():
    # Homopolymer has only one unique 3-mer ("AAA"), so Shannon entropy must be 0.0 bits
    assert compute_kmer_entropy("AAAAAAAAAA", k=3) == 0.0
    # Diverse nucleotide sequence must yield positive Shannon complexity
    entropy = compute_kmer_entropy("ATGCGATCGATCGATCGGCTAGCTAGCT", k=3)
    assert entropy > 2.5

def test_isolation_forest_warmup_and_active_regimes():
    # 1. Warmup regime (< 8 rows)
    warmup_df = pd.DataFrame([
        {"timestamp": "2026-10-02 00:00:00 UTC", "target": f"T{i}", "count": 100, "delta_records": 2, "gc_pct": 50.0, "kmer_entropy": 4.1}
        for i in range(4)
    ])
    scored_warmup, state_w, _ = evaluate_anomalies(warmup_df)
    assert state_w == "MODEL_WARMUP"
    assert (scored_warmup["anomaly_flag"] == "WARMUP").all()

    # 2. Active IsolationForest regime (>= 8 rows)
    active_df = pd.DataFrame([
        {"timestamp": f"2026-10-02 0{i}:00:00 UTC", "target": "T1", "count": 100 + i, "delta_records": 1, "gc_pct": 52.0, "kmer_entropy": 4.2}
        for i in range(10)
    ])
    scored_active, state_a, score_a = evaluate_anomalies(active_df)
    assert state_a in {"NOMINAL", "ANOMALY_DETECTED"}
    assert isinstance(score_a, float)
    assert "anomaly_score" in scored_active.columns
