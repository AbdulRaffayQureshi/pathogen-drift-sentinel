#!/usr/bin/env python3
from collections import Counter
import math
import time
import requests

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
HEADERS = {"User-Agent": "PathogenDriftSentinel/2.1 (Bio-MLOps-Pipeline)"}

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

def _pull_fasta_bases(id_list: list[str]) -> str:
    if not id_list:
        return ""
    time.sleep(0.35)
    fetch_resp = requests.get(
        f"{NCBI_BASE}/efetch.fcgi",
        params={"db": "nuccore", "id": ",".join(id_list), "rettype": "fasta", "retmode": "text"},
        headers=HEADERS,
        timeout=25
    )
    fetch_resp.raise_for_status()
    lines = [line.strip() for line in fetch_resp.text.splitlines() if not line.startswith(">")]
    raw = "".join(lines)
    return "".join([b for b in raw.upper() if b in "ATCG"])[:15000]

def fetch_target_bio_features(query: str) -> dict:
    # Step A: True total record count across all NCBI nuccore divisions
    count_resp = requests.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={"db": "nuccore", "term": query, "retmode": "json", "retmax": 0},
        headers=HEADERS,
        timeout=20
    )
    count_resp.raise_for_status()
    total_count = int(count_resp.json()["esearchresult"]["count"])

    time.sleep(0.35)
    # Step B: Fetch non-scaffold sequence IDs specifically for FASTA GC% & 3-mer extraction
    seq_query = f"({query}) AND biomol_genomic[PROP] NOT gbdiv_con[PROP] NOT wgs[PROP]"
    seq_resp = requests.get(
        f"{NCBI_BASE}/esearch.fcgi",
        params={"db": "nuccore", "term": seq_query, "retmode": "json", "retmax": 8, "sort": "date"},
        headers=HEADERS,
        timeout=20
    )
    seq_resp.raise_for_status()
    id_list = seq_resp.json()["esearchresult"].get("idlist", [])
    concat_seq = _pull_fasta_bases(id_list)

    return {
        "count": total_count,
        "gc_pct": compute_gc_content(concat_seq),
        "kmer_entropy": compute_kmer_entropy(concat_seq, k=3)
    }
