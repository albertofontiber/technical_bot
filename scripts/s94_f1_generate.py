#!/usr/bin/env python3
"""s94_f1_generate.py — F1 del piloto (spec v2): genera los 3 brazos + QA-fila + delta-check.

Por hecho (F0) × padre acreditable (cap 2, regla determinista: primero los que contienen el
valor literal, luego orden de id — declarado):
- REGIÓN = página del store del padre (sha256 + page_number del chunk; búsqueda del valor
  en páginas [p-1, p, p+1] por drift de offsets — se ancla la página donde el valor aparece,
  si no la del chunk).
- R2: LLM (claude-sonnet-4-6) → enunciados autónomos (producto + sección + valores LITERALES
  + discriminador de variante) desde el item que contiene el valor (o la página ≤8k, flag).
- R1: por item-tabla con `rows` en la región: fila→"producto · titulo · h1=v1; h2=v2"
  (rows[0]=cabecera, heurística declarada; isPerfectTable registrado).
- R3: por item-tabla de la región (cap 3): resumen 1-2 frases (propósito + producto + qué lista).

QA (inv.2, anti-mispairing):
(a) todo token numérico/código del texto generado existe en la región fuente (normalizado);
(b) para textos FACT-BEARING (contienen el valor del hecho): la línea/fila fuente del valor
    debe co-ocurrir con ≥1 token discriminador del texto (producto/cabecera, no-stopword).
Fallos → fuera + tasa por brazo.

Delta-check H4 (antes de F2): para los 4 hechos del track C, |Δcos| entre receta
blurb-padre y prefijo-store sobre el mejor enunciado R2 → si > tie-band, R2 corre con
blurb-padre (pre-registrado).

Salida: evals/s94_f1_candidates.json + resumen. Nada se escribe en DB.
"""
import json
import os
import re
import sys

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), ".env"), override=False)
import anthropic
import glob as _glob

from s93_trackB_probe import TIE, fetch_chunks, norm
from src.config import LLM_MODEL
from src.ingestion.embedder import embed_query
from src.rag.retriever import _cos
from src.reingest.embed import embed

STORE = "data/extraction/agent_anthropic-sonnet-45"
TRACKC_FACTS = {("hp011", "05 a 295 seg"), ("hp012", "2 lazos / 396"),
                ("hp014", "35"), ("hp018", "1 A")}
_STOP = {"de", "la", "el", "en", "del", "los", "las", "un", "una", "por", "para", "con",
         "es", "se", "que", "central", "panel", "manual", "seccion", "tabla", "pagina"}

R2_PROMPT = """Convierte el siguiente fragmento de un manual técnico PCI en ENUNCIADOS autónomos, uno por línea.
Reglas ESTRICTAS: cada enunciado expresa UN dato como frase completa en español técnico; incluye SIEMPRE el modelo/producto EXACTO ({producto}) y el contexto de sección; si el dato pertenece a una VARIANTE concreta (nº de lazos, versión, canal), el enunciado DEBE nombrarla; conserva los valores LITERALES (números, unidades, códigos, referencias) sin redondear ni convertir; NADA que no esté en el fragmento; sin comentarios, sin numeración, sin markdown."""

R3_PROMPT = """Describe la siguiente tabla de un manual técnico PCI en 1-2 frases en español técnico: su PROPÓSITO (qué pregunta responde), el producto/modelo EXACTO ({producto}) y qué magnitudes/columnas lista. NO enumeres los valores. Sin markdown."""


def _sha_path(sha: str) -> str | None:
    hits = _glob.glob(f"{STORE}/{sha[:12]}*.json") or _glob.glob(f"{STORE}/*{sha[:12]}*.json")
    if hits:
        return hits[0]
    for p in _glob.glob(f"{STORE}/*.json"):
        with open(p, encoding="utf-8") as fh:
            if f'"{sha}"' in fh.read(400):
                return p
    return None


_DOC_CACHE: dict = {}


def store_pages(sha: str) -> list:
    if sha not in _DOC_CACHE:
        p = _sha_path(sha)
        d = json.load(open(p, encoding="utf-8")) if p else {}
        r = d.get("result") or {}
        _DOC_CACHE[sha] = r.get("pages", []) if isinstance(r, dict) else (r if isinstance(r, list) else [])
    return _DOC_CACHE[sha]


def item_text(it: dict) -> str:
    return it.get("md") or it.get("text") or it.get("value") or ""


def value_pat(valor: str):
    nv = norm(valor)
    return re.compile(rf"(?<![a-z0-9]){re.escape(nv)}(?![a-z0-9])") if nv else None


def find_region(sha: str, page: int, valor: str):
    """(page_idx, items) — página con el valor en [p-1,p,p+1], si no la del chunk."""
    pages = store_pages(sha)
    if not pages:
        return None, []
    pat = value_pat(valor)
    cand = [i for i in (page - 1, page - 2, page) if 0 <= i < len(pages)]  # 1-based → idx
    if pat:
        for i in cand:
            items = pages[i].get("items", []) if isinstance(pages[i], dict) else []
            if any(pat.search(norm(item_text(it))) or
                   any(pat.search(norm(" ".join(map(str, row)))) for row in (it.get("rows") or []))
                   for it in items):
                return i, items
    i = min(max(page - 1, 0), len(pages) - 1)
    return i, (pages[i].get("items", []) if isinstance(pages[i], dict) else [])


def tokens_num(text: str) -> set:
    """Tokens numéricos/código del texto generado (para QA-a)."""
    return {t for t in re.findall(r"[a-z0-9][a-z0-9./+-]{1,}", norm(text))
            if any(c.isdigit() for c in t)}


def region_source_text(items: list) -> str:
    parts = []
    for it in items:
        parts.append(item_text(it))
        for row in (it.get("rows") or []):
            parts.append(" | ".join(str(c) for c in row))
    return "\n".join(parts)


def qa_pass(text: str, items: list, valor: str) -> tuple[bool, str]:
    src_norm = norm(region_source_text(items))
    for t in tokens_num(text):
        if t not in src_norm:
            return False, f"token '{t}' no existe en la región"
    pat = value_pat(valor)
    if pat and pat.search(norm(text)):          # fact-bearing → QA-b co-ocurrencia
        lines = [ln for ln in region_source_text(items).splitlines() if pat.search(norm(ln))]
        if lines:
            disc = [w for w in re.findall(r"[a-z0-9][a-z0-9-]{2,}", norm(text))
                    if w not in _STOP and not w.isdigit() and not pat.search(w)]
            if not any(any(w in norm(ln) for w in disc) for ln in lines):
                return False, "valor sin discriminador co-ocurrente en su línea fuente"
    return True, ""


def main() -> int:
    f0 = json.load(open("evals/s94_f0_testbed.json", encoding="utf-8"))
    client = anthropic.Anthropic()
    parent_chunks = fetch_chunks(sorted({a["id"] for r in f0["rows"] for a in r["acreditables"]}))
    cands, stats = [], {"R1": [0, 0], "R2": [0, 0], "R3": [0, 0]}   # [gen, qa_fail]

    for r in f0["rows"]:
        qid, valor = r["qid"], r["valor"]
        pat = value_pat(valor)
        acred = sorted(r["acreditables"], key=lambda a: (
            not (pat and pat.search(norm((parent_chunks.get(a["id"]) or {}).get("content") or ""))),
            a["id"]))[:2]
        for a in acred:
            if not a["store_sha256"]:
                continue
            pidx, items = find_region(a["store_sha256"], a.get("page") or 1, valor)
            if not items:
                continue
            producto = a.get("pm") or "el equipo del manual"
            fact_items = [(j, it) for j, it in enumerate(items)
                          if pat and (pat.search(norm(item_text(it))) or
                          any(pat.search(norm(" ".join(map(str, row)))) for row in (it.get("rows") or [])))]
            region_items = [it for _, it in fact_items] or items
            src = region_source_text(region_items)[:8000]

            def add(arm, text, extra):
                stats[arm][0] += 1
                ok, motivo = qa_pass(text, region_items, valor)
                if not ok:
                    stats[arm][1] += 1
                cands.append({"arm": arm, "qid": qid, "valor": valor, "parent_id": a["id"],
                              "anchor": {"sha": a["store_sha256"], "page_idx": pidx, **extra},
                              "text": text, "qa_pass": ok, "qa_motivo": motivo,
                              "fact_bearing": bool(pat and pat.search(norm(text)))})

            # R2
            msg = client.messages.create(model=LLM_MODEL, max_tokens=1500,
                                         system=R2_PROMPT.format(producto=producto),
                                         messages=[{"role": "user", "content": src}])
            for st in (ln.strip() for ln in msg.content[0].text.splitlines() if ln.strip()):
                add("R2", st, {"item": "region"})
            # R1 + R3 sobre items-tabla
            tablas = [(j, it) for j, it in enumerate(items) if it.get("rows")]
            if fact_items:
                tablas = [(j, it) for j, it in tablas if any(j == fj for fj, _ in fact_items)] or tablas[:3]
            for j, it in tablas[:3]:
                rows = it.get("rows") or []
                if len(rows) >= 2:
                    head = [str(h).strip() for h in rows[0]]
                    for ri, row in enumerate(rows[1:], 1):
                        pares = [f"{head[k]}={str(c).strip()}" for k, c in enumerate(row)
                                 if k < len(head) and str(c).strip() and head[k]]
                        if pares:
                            add("R1", f"{producto} · {'; '.join(pares)}",
                                {"item_idx": j, "row_idx": ri, "isPerfect": bool(it.get("isPerfectTable"))})
                msg = client.messages.create(model=LLM_MODEL, max_tokens=300,
                                             system=R3_PROMPT.format(producto=producto),
                                             messages=[{"role": "user", "content": item_text(it)[:6000]}])
                add("R3", msg.content[0].text.strip(), {"item_idx": j})
        print(f"{qid:8} {valor[:20]!r:22} candidatos acumulados={len(cands)}")

    # delta-check H4 (mejor R2 fact-bearing de los 4 hechos track C)
    delta = []
    for (qid, valor) in sorted(TRACKC_FACTS):
        row = next((x for x in f0["rows"] if x["qid"] == qid and x["valor"] == valor), None)
        best = next((c for c in cands if c["qid"] == qid and c["valor"] == valor
                     and c["arm"] == "R2" and c["fact_bearing"] and c["qa_pass"]), None)
        if not (row and best):
            delta.append({"qid": qid, "valor": valor, "delta": None, "motivo": "sin candidato fact-bearing"})
            continue
        ch = parent_chunks.get(best["parent_id"]) or {}
        q_emb = embed_query(row["question"])
        t_b7 = (f"{ch['context']}\n\n{best['text']}" if ch.get("context") else best["text"])
        t_store = f"{ch.get('source_file','doc')} · página {best['anchor'].get('page_idx',0)+1}\n\n{best['text']}"
        e = embed([t_b7, t_store], "document")
        d = abs(_cos(q_emb, e[0]) - _cos(q_emb, e[1]))
        delta.append({"qid": qid, "valor": valor, "delta": round(d, 4), "supera_tie": d > TIE})

    out = {"stats": {k: {"generados": v[0], "qa_fail": v[1]} for k, v in stats.items()},
           "delta_check_prefijo": delta, "candidatos": cands}
    json.dump(out, open("evals/s94_f1_candidates.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\nstats:", out["stats"])
    print("delta-check:", delta)
    fb = sum(1 for c in cands if c["fact_bearing"] and c["qa_pass"])
    print(f"candidatos={len(cands)} (fact-bearing QA-OK={fb}) → evals/s94_f1_candidates.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
