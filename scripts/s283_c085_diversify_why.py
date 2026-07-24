#!/usr/bin/env python3
"""s283_c085_diversify_why.py — ¿por qué cat022 muere en diversify incluso a sim=0.95?

$0. Detecta models de cada query (rama source_file vs manufacturer del diversify),
cuenta source_files/manufacturers del pool post-model_filter, y el max_per_source.
"""
from __future__ import annotations
import os, sys
os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["HYDE_ENABLED"] = "false"
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(os.getcwd()).resolve()
load_dotenv(ROOT / ".env", override=True)
os.environ["CHUNKS_TABLE"] = "chunks_v2"
os.environ.update({
    "COVERAGE_RELEASE_PROFILE": "coverage_c1_v4", "IDENTITY_RESOLVE": "on",
    "IDENTITY_RESOLVE_POLICY": "replace", "MUST_PRESERVE_CONTRACT": "on",
    "ENUNCIADOS_MULTIVECTOR": "on", "HYQ_TABLE": "on", "VISUAL_ASSETS_REGISTRY": "on",
    "RERANK_TOP_K": "10"})
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from collections import Counter
from src.rag.retriever import retrieve_chunks, extract_product_models, RETRIEVAL_TOP_K

QUERIES = {
    "cat022": ("En los detectores de llama Spectrex SharpEye 40/40, ¿qué diferencia hay "
               "entre el modelo 40/40L y el 40/40L4, y qué significa el sufijo «B» (p. ej. 40/40LB)?"),
    "hp012": ("¿Cuántos lazos direccionables soporta la Notifier AM2020/AFP1010 y "
              "cuántos dispositivos por lazo?"),
}

def main():
    for qid, q in QUERIES.items():
        try:
            models = extract_product_models(q)
        except Exception as e:
            models = f"ERR {e}"
        pool = retrieve_chunks(q, top_k=RETRIEVAL_TOP_K)
        src = Counter(c.get("source_file") for c in pool)
        mfr = Counter(c.get("manufacturer") for c in pool)
        print(f"\n### {qid}: models_detected = {models}")
        print(f"   rama diversify = {'source_file (Step 5a)' if models else 'manufacturer (Step 5b)'}")
        print(f"   pool_size={len(pool)}  max_per_source(top_k//3)={max(2, RETRIEVAL_TOP_K//3)}")
        print(f"   source_files en pool: {dict(src.most_common(6))}")
        print(f"   manufacturers en pool: {dict(mfr.most_common(6))}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
