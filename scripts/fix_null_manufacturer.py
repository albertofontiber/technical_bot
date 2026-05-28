#!/usr/bin/env python3
"""#6 — Atribuye manufacturer (y corrige product_model junk) en el bucket
manufacturer IS NULL de CHUNKS_TABLE, vía Haiku sobre el blurb B7 + portada +
legal de cada documento.

Diagnóstico (scripts/diagnose_unknown_bucket.py): 9.260 chunks (40,5%) sin
marca en 499 docs; 96% atribución, resto junk semántico (AC-220=voltaje,
SITIOS-10, UN-10...). documents.manufacturer NO sirve (stale 3-marcas) → se usa
solo como cross-check. La marca vive en el blurb/portada/legal ("by Xtralis",
"de Honeywell # RP1r-Supra").

Estrategia (estilo fix_b5, una pasada por documento):
  Haiku ve (filename + product_model actual + blurbs + portada + legal) y
  devuelve {manufacturer (marca específica), product_model canónico,
  is_real_model, confidence, reasoning}. Marca específica (Notifier/Morley/
  Detnov/Xtralis/Securiton/...), no "Honeywell" salvo irresoluble.

Salida:
  - DRY-RUN (default): genera logs/null_mfr_review_<ts>.json (artefacto de
    revisión humana) + resumen. NO escribe en BD. Haiku SÍ se llama.
  - --apply: tras revisión, escribe a chunks (+documents) SOLO las propuestas
    con confidence>=UMBRAL y manufacturer!=unknown. Snapshot de rollback antes.
    Los is_real_model=false → product_model='unknown'. Baja confianza → se deja
    para revisión manual (queda en el artefacto, no se toca).

Uso (PowerShell):
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/fix_null_manufacturer.py --limit 5
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/fix_null_manufacturer.py
    $env:CHUNKS_TABLE='chunks_v2'; python scripts/fix_null_manufacturer.py --apply
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"), override=True)
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
TABLE = os.environ.get("CHUNKS_TABLE", "chunks")
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
H_WRITE = {**H, "Content-Type": "application/json", "Prefer": "return=minimal"}
HAIKU = "claude-haiku-4-5-20251001"
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CONF_THRESHOLD = 0.75
KNOWN_BRANDS = ["Notifier", "Morley", "Detnov", "Xtralis", "Securiton",
                "Spectrex", "Pfannenberg", "Argus Security", "SenseWare", "Pepperl-Fuchs"]

PROMPT = """Clasificas un manual técnico de PCI (protección contra incendios) en español.
A partir del contexto del documento (blurb, portada, aviso legal), identifica:

- manufacturer: el FABRICANTE real, MARCA ESPECÍFICA (no el distribuidor ni el grupo).
  Marcas en el corpus: {brands}. Si es otra, dila tal cual.
  Si el texto dice "Honeywell" pero el producto es de una marca-hija concreta (Notifier o
  Morley), usa la marca-hija. Usa "Honeywell" SOLO si no puedes determinar la marca-hija.
  Usa "unknown" si no hay ninguna señal de marca.
- product_model: el modelo/producto canónico del que trata el documento (casing y guiones del
  manual). SIEMPRE da tu mejor valor aquí, sea o no igual al actual.
- current_model_ok: true si el product_model ACTUAL ("{current}") ya es un código de modelo
  correcto para este producto; false si es basura o erróneo (p.ej. un voltaje como "AC-220",
  una palabra suelta como "SITIOS-10"/"UN-10"/"DE-12", una fecha o una norma EN) y debe
  reemplazarse por tu product_model.
- confidence: 0.0-1.0 (cómo de seguro estás de la MARCA).
- reasoning: UNA frase citando la evidencia textual (marca/modelo que viste).

Devuelve SOLO JSON, sin prosa:
{{"manufacturer":"...","product_model":"...","current_model_ok":false,"confidence":0.9,"reasoning":"..."}}

Filename: {filename}

--- CONTEXTO DEL DOCUMENTO ---
{ctx}"""


def get(params: dict, table: str = None) -> list[dict]:
    r = httpx.get(f"{URL}/rest/v1/{table or TABLE}", headers=H, params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def fetch_bucket() -> dict[str, dict]:
    """Docs con manufacturer NULL → {source_file: {product_models, document_id}}."""
    rows: list[dict] = []
    offset = 0
    while True:
        b = get({"manufacturer": "is.null",
                 "select": "product_model,source_file,document_id",
                 "order": "id", "limit": "1000", "offset": str(offset)})
        rows.extend(b)
        if len(b) < 1000:
            break
        offset += 1000
    docs: dict[str, dict] = defaultdict(lambda: {"product_models": set(), "document_id": None})
    for r in rows:
        s = r.get("source_file") or "NOSRC"
        docs[s]["product_models"].add(r.get("product_model") or "NULL")
        if r.get("document_id"):
            docs[s]["document_id"] = r["document_id"]
    return docs


def fetch_doc_context(source_file: str) -> str:
    """Blurbs (primeras págs) + portada + legal, recortados a presupuesto."""
    first = get({"source_file": f"eq.{source_file}",
                 "select": "content,context,page_number",
                 "order": "page_number.asc", "limit": "4"})
    last = get({"source_file": f"eq.{source_file}",
                "select": "content,page_number",
                "order": "page_number.desc", "limit": "2"})
    parts: list[str] = []
    blurbs = [f"- {(r.get('context') or '').strip()}" for r in first if r.get("context")]
    if blurbs:
        parts.append("BLURBS:\n" + "\n".join(b[:300] for b in blurbs[:3]))
    if first:
        parts.append(f"PORTADA (p{first[0].get('page_number')}):\n{(first[0].get('content') or '')[:1500]}")
    if last:
        parts.append(f"LEGAL/FINAL (p{last[0].get('page_number')}):\n{(last[0].get('content') or '')[:1000]}")
    return "\n\n".join(parts)


def fetch_documents_mfr(doc_ids: list[str]) -> dict[str, str | None]:
    """documents.manufacturer por id (batches pequeños: GET con muchos UUIDs da 400)."""
    out: dict[str, str | None] = {}
    for i in range(0, len(doc_ids), 40):
        ids = doc_ids[i:i + 40]
        id_list = ",".join(f'"{d}"' for d in ids)
        try:
            for d in get({"id": f"in.({id_list})", "select": "id,manufacturer", "limit": "40"}, table="documents"):
                out[d["id"]] = d.get("manufacturer")
        except Exception:
            pass
    return out


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}


def classify_doc(source_file: str, info: dict) -> dict:
    current = ", ".join(sorted(info["product_models"]))
    ctx = fetch_doc_context(source_file)
    prompt = PROMPT.format(brands=", ".join(KNOWN_BRANDS), current=current,
                           filename=source_file, ctx=ctx[:6000])
    try:
        resp = client.messages.create(
            model=HAIKU, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        data = parse_json(resp.content[0].text)
    except Exception as e:
        data = {"error": str(e)}
    return {
        "source_file": source_file,
        "document_id": info["document_id"],
        "current_product_models": sorted(info["product_models"]),
        "proposed_manufacturer": data.get("manufacturer"),
        "proposed_product_model": data.get("product_model"),
        "current_model_ok": data.get("current_model_ok"),
        "confidence": data.get("confidence"),
        "reasoning": data.get("reasoning"),
        "error": data.get("error"),
    }


def apply_changes(proposals: list[dict]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Rollback snapshot: valores actuales de los chunks afectados.
    affected_srcs = [p["source_file"] for p in proposals
                     if p.get("confidence", 0) and p["confidence"] >= CONF_THRESHOLD
                     and p.get("proposed_manufacturer") and p["proposed_manufacturer"] != "unknown"]
    snap: list[dict] = []
    for s in affected_srcs:
        rows = get({"source_file": f"eq.{s}", "manufacturer": "is.null",
                    "select": "id,manufacturer,product_model"})
        snap.extend(rows)
    snap_path = os.path.join(ROOT, "logs", f"null_mfr_rollback_{ts}.json")
    os.makedirs(os.path.dirname(snap_path), exist_ok=True)
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)
    print(f"Rollback snapshot ({len(snap)} chunks) -> {snap_path}")

    applied = 0
    for p in proposals:
        conf = p.get("confidence") or 0
        mfr = p.get("proposed_manufacturer")
        if conf < CONF_THRESHOLD or not mfr or mfr == "unknown":
            continue
        s = p["source_file"]
        # 1) manufacturer a nivel documento (todas las filas sin marca del doc)
        httpx.patch(f"{URL}/rest/v1/{TABLE}", headers=H_WRITE,
                    params={"source_file": f"eq.{s}", "manufacturer": "is.null"},
                    json={"manufacturer": mfr}, timeout=30.0).raise_for_status()
        # 2) corregir product_model SOLO si el actual es basura y hay un único
        #    valor → se acota a ese valor (no clobbering si hubiera varios modelos)
        cur = p.get("current_product_models") or []
        newpm = p.get("proposed_product_model")
        # Setear product_model si el actual es basura (cur_ok=False) o NULL, y hay
        # un único valor actual y Haiku propone un modelo real.
        needs_pm = p.get("current_model_ok") is False or (len(cur) == 1 and cur[0] == "NULL")
        if needs_pm and len(cur) == 1 and newpm and newpm != "unknown":
            old_pm = cur[0]
            pm_filter = {"product_model": "is.null"} if old_pm == "NULL" else {"product_model": f"eq.{old_pm}"}
            httpx.patch(f"{URL}/rest/v1/{TABLE}", headers=H_WRITE,
                        params={"source_file": f"eq.{s}", **pm_filter},
                        json={"product_model": newpm}, timeout=30.0).raise_for_status()
        # 3) documents.manufacturer (consistencia)
        if p.get("document_id"):
            httpx.patch(f"{URL}/rest/v1/documents", headers=H_WRITE,
                        params={"id": f"eq.{p['document_id']}"},
                        json={"manufacturer": mfr}, timeout=30.0)
        applied += 1
    print(f"Aplicadas {applied} propuestas (>= conf {CONF_THRESHOLD}).")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="escribe en BD (default: dry-run)")
    ap.add_argument("--limit", type=int, default=0, help="procesa solo N docs (validación)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    print(f"== fix_null_manufacturer · tabla='{TABLE}' · {'APPLY' if args.apply else 'DRY-RUN'} ==\n")
    docs = fetch_bucket()
    items = sorted(docs.items())
    if args.limit:
        items = items[:args.limit]
    print(f"Docs a clasificar: {len(items)}")

    doc_ids = [v["document_id"] for _, v in items if v["document_id"]]
    docs_mfr = fetch_documents_mfr(doc_ids)

    proposals: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(classify_doc, s, info): s for s, info in items}
        for i, fut in enumerate(as_completed(futs), 1):
            p = fut.result()
            p["documents_mfr_crosscheck"] = docs_mfr.get(p.get("document_id"))
            proposals.append(p)
            if i % 25 == 0:
                print(f"  ...{i}/{len(items)}")

    proposals.sort(key=lambda p: (p.get("confidence") or 0))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    art = os.path.join(ROOT, "logs", f"null_mfr_review_{ts}.json")
    os.makedirs(os.path.dirname(art), exist_ok=True)
    with open(art, "w", encoding="utf-8") as f:
        json.dump(proposals, f, ensure_ascii=False, indent=2)

    # Resumen
    from collections import Counter
    by_mfr = Counter(p.get("proposed_manufacturer") or "∅" for p in proposals)
    n_lowconf = sum(1 for p in proposals if (p.get("confidence") or 0) < CONF_THRESHOLD)
    n_junk = sum(1 for p in proposals if p.get("current_model_ok") is False)
    n_err = sum(1 for p in proposals if p.get("error"))
    print(f"\nPropuestas: {len(proposals)}")
    print(f"  por marca: {dict(by_mfr.most_common())}")
    print(f"  baja confianza (<{CONF_THRESHOLD}, a revisión manual): {n_lowconf}")
    print(f"  product_model junk (is_real_model=false): {n_junk}")
    print(f"  errores Haiku: {n_err}")
    print(f"\nMuestra (15 propuestas de menor confianza primero):")
    for p in proposals[:15]:
        print(f"  conf={p.get('confidence')} [{p.get('proposed_manufacturer')}] "
              f"{p['source_file']}: {p['current_product_models']} -> "
              f"model={p.get('proposed_product_model')} cur_ok={p.get('current_model_ok')} "
              f"docX={p.get('documents_mfr_crosscheck')}")
        print(f"      {p.get('reasoning')}")
    print(f"\nArtefacto -> {art}")

    if args.apply:
        print("\n== APPLY ==")
        apply_changes(proposals)


if __name__ == "__main__":
    main()
