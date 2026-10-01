#!/usr/bin/env python3
from collections import Counter
import math
import time
import requests

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HEADERS = {"User-Agent": "PathogenDriftSentinel/2.0 (Bio-MLOps-Pipeline)"}

def compute_kmer_entropy(seq: str, k: int = 3) -> float:
    seq = "".join([b for b in seq.upper() if b in "ATCG"])
    if len(seq) < k:
        return 0.0
    kmers = [seq[i:i+k] for i in range(len(seq) - k + 1)]
    counts = Counter(kmers)
    total = len(kmers)
    return round(-sum((c / total) * math.log2(c / total) for c in counts.values()), 4)

def compute_gc_content(seq: str) -> float:
    seq = "".join([b for b in seq.upper() if b in "ATCG"])
    if not seq:
        return 0.0
    gc = sum(1 for b in seq if b in "GC")
    return round((gc / len(seq)) * 100.0, 2)

def fetch_target_bio_features(query: str) -> dict:
    # 1. Search nuccore for total count + latest 3 sequence IDs
    search_resp = requests.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={"db": "nuccore", "term": query, "retmode": "json", "retmax": 3, "sort": "date"},
        headers=HEADERS,
        timeout=20
    )
    search_resp.raise_for_status()
    res = search_resp.json()["esearchresult"]
    total_count = int(res["count"])
    id_list = res.get("idlist", [])

    if not id_list:
        return {"count": total_count, "gc_pct": 50.0, "kmer_entropy": 4.0}

    time.sleep(0.35)
    # 2. Fetch raw FASTA for latest sequences to compute genomic drift features
    fetch_resp = requests.get(
        f"{NCBI_BASE}/efetch.fcgi",
        params={"db": "nuccore", "id": ",".join(id_list), "rettype": "fasta", "retmode": "text"},
        headers=HEADERS,
        timeout=25
    )
    fetch_resp.raise_for_status()

    lines = [line.strip() for line in fetch_resp.text.splitlines() if not line.startswith(">")]
    concat_seq = "".join(lines)[:15000]  # Cap at 15kb for fast CI processing

    return {
        "count": total_count,
        "gc_pct": compute_gc_content(concat_seq),
        "kmer_entropy": compute_kmer_entropy(concat_seq, k=3)
    }
