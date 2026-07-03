#!/usr/bin/env python3
"""enunciados_pass.py — el PASE corpus de enunciados por tramos (T0-4, plan s94b v2).

Por doc del store (agent_anthropic-sonnet-45) × página × item-de-datos:
  R2: enunciados LLM (PROMPT v1 CONGELADO — el del piloto DEC-086, con regla de
      discriminador de variante) por item.   R3: resumen 1-2 frases por item-tabla.
QA gate: `enunciados_qa.qa_statement` (fidelidad + anti-mispairing fila-nivel,
calibrado: caza 2/2 alucinaciones del piloto). Solo QA-OK se inserta.

Contrato de fila (migración 007 + dúo s94b):
  id            = uuid5(ancla) → IDEMPOTENTE (re-corrida = mismos ids)
  parent_id     = chunk del mismo source_file/página con máx. solape de tokens-valor
                  (tie → chunk_index menor). Sin padre resoluble → item FUERA (declarado).
  extraction_sha256 = el del DOC REAL (semántica intacta: re-proceso del manual borra
                  por sha → arrastra surrogates; + ON DELETE CASCADE por parent_id)
  ingest_batch  = 'enunciados-v1:<tranche>:p1' → rollback selectivo + vintage visible
  context       = blurb-B7 del padre · embedding = embed(context+"\\n\\n"+texto) (receta corpus)

Idempotencia de tramo: DELETE por ingest_batch ANTES de insertar. Cobertura por doc +
muestreo estratificado (marca × isPerfectTable) a evals/enunciados_sample_<tranche>.md.

Uso:
  python scripts/enunciados_pass.py --tranche T1 --docs <fichero con source_files> [--dry]
  python scripts/enunciados_pass.py --rollback enunciados-v1:T1
"""
import argparse
import glob
import json
import os
import re
import sys
import uuid
from collections import defaultdict

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import anthropic
import httpx

from enunciados_qa import cobertura_pagina, qa_statement, tokens_valor
from s94_f1_generate import item_text, store_pages
from src.config import LLM_MODEL, SUPABASE_SERVICE_KEY, SUPABASE_URL

NAMESPACE = uuid.UUID("6d0c6f2a-94b4-4e10-9c1e-a1b2c3d4e5f6")   # fijo: ids idempotentes uuid5(ancla)
STORE = "data/extraction/agent_anthropic-sonnet-45"
_H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
      "Content-Type": "application/json"}

# PROMPTS v1 CONGELADOS (= piloto DEC-086; NO editar — un cambio es p2 y se declara)
R2_PROMPT_V1 = """Convierte el siguiente fragmento de un manual técnico PCI en ENUNCIADOS autónomos, uno por línea.
Reglas ESTRICTAS: cada enunciado expresa UN dato como frase completa en español técnico; incluye SIEMPRE el modelo/producto EXACTO ({producto}) y el contexto de sección; si el dato pertenece a una VARIANTE concreta (nº de lazos, versión, canal), el enunciado DEBE nombrarla; conserva los valores LITERALES (números, unidades, códigos, referencias) sin redondear ni convertir; NADA que no esté en el fragmento; sin comentarios, sin numeración, sin markdown."""
R3_PROMPT_V1 = """Describe la siguiente tabla de un manual técnico PCI en 1-2 frases en español técnico: su PROPÓSITO (qué pregunta responde), el producto/modelo EXACTO ({producto}) y qué magnitudes/columnas lista. NO enumeres los valores. Sin markdown."""


def doc_chunks(source_file: str) -> list[dict]:
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H, params={
        "select": "id,content,context,product_model,manufacturer,source_file,page_number,"
                  "language,document_id,section_title,doc_type,content_type,chunk_index,"
                  "extraction_sha256",
        "source_file": f"eq.{source_file}", "parent_id": "is.null",
        "duplicate_of": "is.null", "limit": "2000"}, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_parent(item_txt: str, page_1b: int, chunks: list[dict]) -> dict | None:
    """Padre = chunk de la página con máx. solape de tokens-valor (tie → chunk_index)."""
    cand = [c for c in chunks if c.get("page_number") == page_1b] or chunks
    if not cand:
        return None
    vals = tokens_valor(item_txt)

    def score(c):
        return len(vals & tokens_valor(c.get("content") or ""))

    best = min(cand, key=lambda c: (-score(c), c.get("chunk_index") or 0))
    if vals and score(best) == 0:          # el item no vive en ningún chunk → sin padre
        return None
    return best


def sha_of(source_file: str) -> str | None:
    key = re.sub(r"[^a-z0-9]", "", source_file.lower())
    for p in glob.glob(f"{STORE}/*.json"):
        head = open(p, encoding="utf-8").read(600)
        m = re.search(r'"source_path":\s*"([^"]+)"', head)
        if m and key and key in re.sub(r"[^a-z0-9]", "", m.group(1).lower()):
            m2 = re.search(r'"sha256":\s*"([0-9a-f]{16,})"', head)
            return m2.group(1) if m2 else None
    return None


def process_doc(client, source_file: str, tranche: str, dry: bool) -> dict:
    from src.reingest.embed import embed
    sha = sha_of(source_file)
    if not sha:
        return {"doc": source_file, "error": "sin store"}
    chunks = doc_chunks(source_file)
    if not chunks:
        return {"doc": source_file, "error": "sin chunks en DB"}
    marca = chunks[0].get("manufacturer") or "?"
    batch = f"enunciados-v1:{tranche}:p1"
    rows, sample, stats = [], [], {"items": 0, "gen": 0, "qa_fail": 0, "sin_padre": 0}
    cov_by_page = []
    for pidx, page in enumerate(store_pages(sha)):
        items = page.get("items", []) if isinstance(page, dict) else []
        data_items = [(j, it) for j, it in enumerate(items)
                      if it.get("rows") or len(tokens_valor(item_text(it))) >= 3]
        page_stmts: list[str] = []
        for j, it in enumerate(items):
            if (j, it) not in data_items:
                continue
            stats["items"] += 1
            parent = resolve_parent(item_text(it), pidx + 1, chunks)
            if parent is None:
                stats["sin_padre"] += 1
                continue
            producto = parent.get("product_model") or "el equipo del manual"
            wl = " ".join(str(parent.get(k) or "") for k in
                          ("product_model", "manufacturer", "source_file"))
            outs = []
            msg = client.messages.create(model=LLM_MODEL, max_tokens=1500,
                                         system=R2_PROMPT_V1.format(producto=producto),
                                         messages=[{"role": "user",
                                                    "content": item_text(it)[:8000]}])
            outs += [("R2", ln.strip()) for ln in msg.content[0].text.splitlines() if ln.strip()]
            if it.get("rows"):
                msg = client.messages.create(model=LLM_MODEL, max_tokens=300,
                                             system=R3_PROMPT_V1.format(producto=producto),
                                             messages=[{"role": "user",
                                                        "content": item_text(it)[:6000]}])
                outs.append(("R3", msg.content[0].text.strip()))
            for arm, text in outs:
                stats["gen"] += 1
                ok, motivo = qa_statement(text, [it], wl)
                if not ok:
                    stats["qa_fail"] += 1
                    continue
                page_stmts.append(text)
                ancla = f"{sha}:{pidx}:{j}:{arm}:{len(rows)}"
                rows.append({
                    "id": str(uuid.uuid5(NAMESPACE, ancla)),
                    "content": text, "context": parent.get("context"),
                    "parent_id": parent["id"], "ingest_batch": batch,
                    "extraction_sha256": parent.get("extraction_sha256") or sha,
                    **{k: parent.get(k) for k in
                       ("product_model", "manufacturer", "source_file", "language",
                        "document_id", "section_title", "doc_type", "content_type",
                        "chunk_index")},
                    "page_number": pidx + 1,
                })
                if it.get("rows") is not None and len(sample) < 3:
                    sample.append({"marca": marca, "isPerfect": bool(it.get("isPerfectTable")),
                                   "text": text[:160]})
        cov = cobertura_pagina(items, page_stmts)
        if cov is not None:
            cov_by_page.append(cov)
    if not dry and rows:
        from src.reingest.embed import embed as _embed
        texts = [(f"{r['context']}\n\n{r['content']}" if r.get("context") else r["content"])
                 for r in rows]
        embs = []
        for i in range(0, len(texts), 100):
            embs.extend(_embed(texts[i:i + 100], "document"))
        for r, e in zip(rows, embs):
            r["embedding"] = e
        for i in range(0, len(rows), 50):
            resp = httpx.post(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                              headers={**_H, "Prefer": "return=minimal"},
                              json=rows[i:i + 50], timeout=60)
            resp.raise_for_status()
    cov_doc = sum(cov_by_page) / len(cov_by_page) if cov_by_page else None
    return {"doc": source_file, "marca": marca, "insertables": len(rows),
            "cobertura": round(cov_doc, 3) if cov_doc is not None else None,
            "sample": sample, **stats}


def rollback(batch_prefix: str) -> int:
    r = httpx.delete(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                     headers={**_H, "Prefer": "return=minimal"},
                     params={"ingest_batch": f"like.{batch_prefix}*"}, timeout=120)
    r.raise_for_status()
    chk = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                    params={"select": "id", "ingest_batch": f"like.{batch_prefix}*",
                            "limit": "1"}, timeout=30)
    n = len(chk.json())
    print(f"[rollback {batch_prefix}] restantes: {n}")
    return 0 if n == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tranche")
    ap.add_argument("--docs", help="fichero con un source_file por línea")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--rollback")
    a = ap.parse_args()
    if a.rollback:
        return rollback(a.rollback)
    assert a.tranche and a.docs, "--tranche y --docs son obligatorios"
    docs = [ln.strip() for ln in open(a.docs, encoding="utf-8") if ln.strip()]
    batch = f"enunciados-v1:{a.tranche}:p1"
    if not a.dry:
        rollback(batch)                       # idempotencia de tramo
    client = anthropic.Anthropic()
    results = []
    for i, doc in enumerate(docs):
        res = process_doc(client, doc, a.tranche, a.dry)
        results.append(res)
        print(f"[{i+1}/{len(docs)}] {doc[:44]:46} ins={res.get('insertables','-'):4} "
              f"qa_fail={res.get('qa_fail','-')} cov={res.get('cobertura','-')} "
              f"{res.get('error','')}")
    out = f"evals/enunciados_pass_{a.tranche}{'_dry' if a.dry else ''}.json"
    json.dump({"tranche": a.tranche, "batch": batch, "dry": a.dry,
               "prompt_vintage": "p1", "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"→ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
