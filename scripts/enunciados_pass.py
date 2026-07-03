#!/usr/bin/env python3
"""enunciados_pass.py — el PASE corpus de enunciados por tramos (T0-4, plan s94b v2).

Por doc del store (agent_anthropic-sonnet-45) × página × item-de-datos:
  R2: enunciados LLM (PROMPT v1 CONGELADO — el del piloto DEC-086, con regla de
      discriminador de variante) por item.   R3: resumen 1-2 frases por item-tabla.
QA gate: `enunciados_qa.qa_statement` (fidelidad + anti-mispairing fila-nivel,
calibrado: caza 2/2 alucinaciones del piloto). Solo QA-OK se inserta.

Contrato de fila (migración 007 + dúo s94b):
  id            = uuid5(ancla) → estable DENTRO de una generación; la idempotencia
                  OPERATIVA la da el delete por-DOC previo al insert (dúo H4/H7 — una
                  re-generación LLM produce otros textos/ids; temperature=0 pineada)
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
from concurrent.futures import ThreadPoolExecutor
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

def _msg_text(msg) -> str:
    """Texto robusto: la familia Claude 5 emite ThinkingBlock antes del TextBlock —
    content[0].text peta (cazado en el brazo p2). Concatena solo bloques text."""
    return "".join(getattr(b, "text", "") for b in msg.content
                   if getattr(b, "type", "") == "text")


def _temp_kw() -> dict:
    """temperature=0 solo donde el modelo lo acepta: la familia Claude 5 lo DEPRECÓ
    (400 explícito, cazado en el brazo p2). Vintage declarado: p1 pineado a 0;
    p2 con el default del modelo."""
    return {} if "-5" in str(LLM_MODEL) or "fable" in str(LLM_MODEL) else {"temperature": 0}


def _insert_rows(rows: list, poison_log: list) -> int:
    """Insert con BISECCIÓN de filas venenosas (un 500 de PostgREST suele ser UNA fila
    que revienta un trigger — cazado en 15088SP): si un batch falla se parte en dos
    hasta aislar la(s) fila(s), que se loguean y SALTAN (drop medido, no crash)."""
    if not rows:
        return 0
    r = httpx.post(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                   headers={**_H, "Prefer": "return=minimal"},
                   json=rows, timeout=120)
    if r.status_code < 300:
        return len(rows)
    if len(rows) == 1:
        poison_log.append({"id": rows[0]["id"], "source_file": rows[0].get("source_file"),
                           "status": r.status_code, "err": r.text[:200],
                           "content_head": (rows[0].get("content") or "")[:120]})
        return 0
    mid = len(rows) // 2
    return _insert_rows(rows[:mid], poison_log) + _insert_rows(rows[mid:], poison_log)


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
    # Fallback ACOTADO a ±1 página (cross-model T0 + dúo H6: el fallback a doc-entero
    # amplificaba mispairing que nadie caza; el drift real store↔DB es de ±1). Más allá
    # → sin_padre (declarado).
    cand = [c for c in chunks if c.get("page_number") == page_1b]
    if not cand:
        cand = [c for c in chunks if c.get("page_number") in (page_1b - 1, page_1b + 1)]
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
        def _gen_item(par):
            """Fase LLM de un item (paralela: el SDK es thread-safe y reintenta 429)."""
            j, it, parent = par
            producto = parent.get("product_model") or "el equipo del manual"
            outs = []
            msg = client.messages.create(model=LLM_MODEL, max_tokens=1500, **_temp_kw(),
                                         system=R2_PROMPT_V1.format(producto=producto),
                                         messages=[{"role": "user",
                                                    "content": item_text(it)[:8000]}])
            outs += [("R2", ln.strip()) for ln in _msg_text(msg).splitlines() if ln.strip()]
            if it.get("rows"):
                msg = client.messages.create(model=LLM_MODEL, max_tokens=300, **_temp_kw(),
                                             system=R3_PROMPT_V1.format(producto=producto),
                                             messages=[{"role": "user",
                                                        "content": item_text(it)[:6000]}])
                outs.append(("R3", _msg_text(msg).strip()))
            return j, it, parent, outs

        pend = []
        for j, it in enumerate(items):
            if (j, it) not in data_items:
                continue
            stats["items"] += 1
            parent = resolve_parent(item_text(it), pidx + 1, chunks)
            if parent is None:
                stats["sin_padre"] += 1
                continue
            pend.append((j, it, parent))
        with ThreadPoolExecutor(max_workers=4) as ex:
            resultados = list(ex.map(_gen_item, pend))
        for j, it, parent, outs in resultados:
            wl = " ".join(str(parent.get(k) or "") for k in
                          ("product_model", "manufacturer", "source_file"))
            n_item = 0
            for arm, text in outs:
                stats["gen"] += 1
                ok, motivo = qa_statement(text, [it], wl)
                if not ok:
                    stats["qa_fail"] += 1
                    continue
                page_stmts.append(text)
                # contador POR-ITEM (MENOR del cross-model: len(rows) global dependía de
                # omisiones previas → ids no estables entre reruns)
                ancla = f"{sha}:{pidx}:{j}:{arm}:{n_item}"
                n_item += 1
                rows.append({
                    "id": str(uuid.uuid5(NAMESPACE, ancla)),
                    "content": text.replace(chr(0), "")[:8000],
                    "context": parent.get("context"),
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
    if not dry:
        # idempotencia POR-DOC (dúo H4: el rollback global re-pagaba el tramo entero
        # tras un crash en el doc N): borrar SOLO lo previo de este doc+batch.
        httpx.delete(f"{SUPABASE_URL}/rest/v1/chunks_v2",
                     headers={**_H, "Prefer": "return=minimal"},
                     params={"ingest_batch": f"eq.{batch}",
                             "source_file": f"eq.{source_file}"},
                     timeout=60).raise_for_status()
    if not dry and rows:
        from src.reingest.embed import embed as _embed
        texts = [(f"{r['context']}\n\n{r['content']}" if r.get("context") else r["content"])
                 for r in rows]
        embs = []
        for i in range(0, len(texts), 100):
            embs.extend(_embed(texts[i:i + 100], "document"))
        for r, e in zip(rows, embs):
            r["embedding"] = e
        poison: list = []
        for i in range(0, len(rows), 50):
            _insert_rows(rows[i:i + 50], poison)
        if poison:
            stats["filas_venenosas"] = len(poison)
            with open(f"evals/enunciados_poison_{tranche}.jsonl", "a", encoding="utf-8") as fh:
                for x in poison:
                    fh.write(json.dumps(x, ensure_ascii=False) + "\n")
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
    ap.add_argument("--resume", action="store_true",
                    help="salta docs que YA tienen filas en el batch (no re-paga LLM)")
    ap.add_argument("--model", default=None,
                    help="override del modelo LLM (side-by-side p2; default LLM_MODEL)")
    ap.add_argument("--rollback")
    a = ap.parse_args()
    if a.rollback:
        return rollback(a.rollback)
    assert a.tranche and a.docs, "--tranche y --docs son obligatorios"
    docs = [ln.strip() for ln in open(a.docs, encoding="utf-8") if ln.strip()]
    batch = f"enunciados-v1:{a.tranche}:p1"
    # (dúo H4) SIN rollback global aquí: la idempotencia es por-DOC dentro de
    # process_doc → una re-corrida tras crash salta lo ya pagado (--rollback existe
    # como comando explícito para limpiar un tramo entero).
    if a.model:
        globals()["LLM_MODEL"] = a.model         # override declarado (vintage distinto)
    client = anthropic.Anthropic()
    results = []
    for i, doc in enumerate(docs):
        if a.resume and not a.dry:
            chk = httpx.get(f"{SUPABASE_URL}/rest/v1/chunks_v2", headers=_H,
                            params={"select": "id", "ingest_batch": f"eq.{batch}",
                                    "source_file": f"eq.{doc}", "limit": "1"}, timeout=15)
            if chk.status_code == 200 and chk.json():
                print(f"[{i+1}/{len(docs)}] {doc[:44]:46} RESUME: ya en batch, saltado")
                results.append({"doc": doc, "skipped": True})
                continue
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
