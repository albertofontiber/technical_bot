#!/usr/bin/env python3
"""Fix B5 — corrige product_model = código de documento → producto real.

Problema (sesión 27): ~246 docs de chunks_v2 tienen product_model = código de
documento (MPDT-190, MCDT-191, HOP-138...) en vez del producto real (ID3000,
INSPIRE). B5 (metadata.py) leyó el código del filename y lo trató como modelo.
Esto rompe filter_product del retriever: la query "ID3000" no matchea chunks
con product_model="MPDT-190".

Solución: el blurb contextual B7 (Haiku, ya en chunks_v2) dice de qué producto
trata el documento ("portada del manual de programación de la Central ID3000").
Es señal más limpia que MODEL_PATTERN sobre content crudo (que cuenta menciones
y confunde CFP-800 con un "DT-020"). Para cada doc afectado:
  1. Recolectar los blurbs B7 de las primeras páginas.
  2. Haiku identifica el producto canónico del que trata el documento.
  3. Validar contra MODEL_PATTERN del retriever (¿lo reconocería en una query?).
  4. Tabla viejo→nuevo→reconocido para validación humana ANTES del UPDATE.

Uso:
    python scripts/fix_b5_product_model.py            # dry-run: genera tabla
    python scripts/fix_b5_product_model.py --apply     # aplica UPDATE a chunks_v2
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict

import httpx
from anthropic import Anthropic
from dotenv import load_dotenv

# Reutilizamos la MISMA regex que el retriever usa sobre la query → validamos
# si el producto detectado queda en el formato que filter_product reconoce.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.rag.retriever import MODEL_PATTERN  # noqa: E402

load_dotenv()
URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HAIKU = "claude-haiku-4-5-20251001"

# Prefijos de CÓDIGO DE DOCUMENTO (no producto). Un product_model que empiece
# por estos es síntoma del bug.
DOC_CODE_RE = re.compile(
    r"^(M[ACFINP]-?DT|HOP|TG-|HLSI|\d{4,})", re.IGNORECASE
)

BLURBS_PER_DOC = 5      # cuántos blurbs (de páginas bajas) pasar a Haiku
OUTPUT_TABLE = "evals/b5_fix_plan.json"

_PROMPT = (
    "Eres experto en catálogo de productos PCI (paneles y detección contra "
    "incendios: Notifier, Detnov, Morley, Honeywell). Te doy descripciones de "
    "fragmentos de UN documento técnico.\n\n"
    "Identifica el ÚNICO producto/modelo principal del que trata el documento.\n\n"
    "Reglas:\n"
    "- Devuelve SOLO el código de modelo canónico (ej: ID3000, AFP-400, "
    "INSPIRE E10, CFP-800, NFS Supra).\n"
    "- Si trata de software/herramienta sin hardware, devuelve su nombre.\n"
    "- Si NO hay un producto único identificable (genérico, multi-producto, "
    "índice), responde exactamente: NONE\n"
    "- NO inventes. Usa solo lo que aparece en las descripciones.\n"
    "- Responde en UNA línea: el modelo y nada más.\n\n"
    "Descripciones:\n{blurbs}"
)


def fetch_all(client: httpx.Client, params: dict) -> list[dict]:
    """GET paginado a chunks_v2."""
    out: list[dict] = []
    offset = 0
    while True:
        h = {**H, "Range-Unit": "items", "Range": f"{offset}-{offset+999}"}
        r = client.get(f"{URL}/rest/v1/chunks_v2", headers=h, params=params)
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            break
        out.extend(rows)
        if len(rows) < 1000:
            break
        offset += 1000
    return out


def is_doc_code(model: str | None) -> bool:
    return bool(model and DOC_CODE_RE.match(model))


def recognized_by_retriever(model: str) -> bool:
    """¿MODEL_PATTERN del retriever reconocería este modelo en una query?
    Si sí, filter_product podrá activarse para él."""
    return bool(MODEL_PATTERN.search(model))


def canonicalize(model: str) -> str:
    """Forma canónica del product_model (regla sesión 27):
      1. Si MODEL_PATTERN lo captura → ese match en upper (forma exacta que el
         retriever extrae de una query → matching garantizado).
      2. Si no → Haiku raw limpio (antes de '/', upper, trim).
    La normalización bidireccional definitiva es Pieza 3 / Fase 2.
    """
    m = MODEL_PATTERN.search(model)
    if m:
        return m.group(0).upper().strip()
    return model.split("/")[0].strip().upper()


def detect_product_via_haiku(client: Anthropic, blurbs: list[str]) -> str | None:
    """Haiku identifica el producto del que trata el documento, leyendo los
    blurbs B7 de portada. Devuelve None si Haiku responde NONE o falla."""
    joined = "\n".join(f"- {b}" for b in blurbs if b)
    if not joined.strip():
        return None
    try:
        resp = client.messages.create(
            model=HAIKU,
            max_tokens=30,
            messages=[{"role": "user",
                       "content": _PROMPT.format(blurbs=joined[:4000])}],
        )
        out = resp.content[0].text.strip()
        if not out or out.upper() == "NONE":
            return None
        # Defensa: si Haiku devuelve el propio código de documento (MN-DT-512),
        # no es un producto real → None.
        if is_doc_code(out.replace(" ", "")):
            return None
        return out
    except Exception as e:
        print(f"  Haiku falló: {e}")
        return None


def main() -> int:
    apply = "--apply" in sys.argv
    client = httpx.Client(timeout=180.0)

    # Modo --apply: lee el plan validado del JSON (no re-llama a Haiku).
    if apply:
        return apply_plan(client)

    # 1) Todos los chunks (product_model + source_file + page + context)
    print("Cargando chunks_v2...")
    rows = fetch_all(client, {
        "select": "source_file,product_model,page_number,context,manufacturer",
    })
    print(f"  {len(rows)} chunks")

    by_file: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_file[r["source_file"]].append(r)

    affected = {sf: chs for sf, chs in by_file.items()
                if is_doc_code(chs[0].get("product_model"))}
    print(f"  docs afectados (product_model = código): {len(affected)}")

    # 2) Haiku sobre los blurbs de portada de cada doc afectado
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
    plan: list[dict] = []
    print(f"  consultando Haiku sobre {len(affected)} docs...")
    for i, (sf, chs) in enumerate(sorted(affected.items()), 1):
        old_model = chs[0].get("product_model")
        # blurbs de las páginas más bajas (portada/título)
        chs_sorted = sorted(
            chs, key=lambda c: c.get("page_number") or 9999)
        blurbs = [c.get("context") for c in chs_sorted[:BLURBS_PER_DOC]]
        new_model = detect_product_via_haiku(anthropic, blurbs)
        recognized = recognized_by_retriever(new_model) if new_model else False
        plan.append({
            "source_file": sf,
            "old_model": old_model,
            "new_model": new_model,
            "recognized_by_retriever": recognized,
            "n_chunks": len(chs),
        })
        if i % 25 == 0:
            print(f"    {i}/{len(affected)}")

    # 3) Guardar plan + reporte
    with open(OUTPUT_TABLE, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    resolved = [p for p in plan if p["new_model"]]
    recog = [p for p in resolved if p["recognized_by_retriever"]]
    unrecog = [p for p in resolved if not p["recognized_by_retriever"]]
    nones = [p for p in plan if not p["new_model"]]

    print(f"\n{'='*72}")
    print(f"RESUELTOS: {len(resolved)}/{len(plan)}  |  "
          f"reconocidos por retriever: {len(recog)}  |  "
          f"no reconocidos: {len(unrecog)}  |  NONE: {len(nones)}")
    print(f"{'='*72}")
    for p in plan:
        if not p["new_model"]:
            flag = "NONE"
        elif p["recognized_by_retriever"]:
            flag = " OK "
        else:
            flag = "????"  # producto detectado pero fuera del vocab del retriever
        print(f"[{flag}] {str(p['old_model']):13} -> {str(p['new_model']):16} "
              f"[{p['source_file'][:42]}]")

    print(f"\nPlan guardado en {OUTPUT_TABLE}")
    print(f"[DRY-RUN] Revisa la tabla. Re-ejecuta con --apply para aplicar "
          f"los {len(resolved)} cambios resueltos.")
    print(f"NOTA: los '????' tienen producto correcto en metadata pero el "
          f"retriever (MODEL_PATTERN) no los reconocería en query → gap "
          f"separado de cobertura del retriever.")
    return 0


def apply_plan(client: httpx.Client) -> int:
    """Lee evals/b5_fix_plan.json (validado) y aplica los UPDATE."""
    with open(OUTPUT_TABLE, encoding="utf-8") as f:
        plan = json.load(f)
    resolved = [p for p in plan if p["new_model"]]
    print(f"Aplicando UPDATE a {len(resolved)} docs (de {len(plan)} afectados)...")
    n_chunks = 0
    for p in resolved:
        canonical = p.get("canonical_model") or canonicalize(p["new_model"])
        r = client.patch(
            f"{URL}/rest/v1/chunks_v2",
            headers={**H, "Prefer": "return=minimal"},
            params={"source_file": f"eq.{p['source_file']}"},
            json={"product_model": canonical},
        )
        if r.status_code >= 400:
            print(f"  ERROR {r.status_code} en {p['source_file']}: {r.text[:150]}")
        else:
            n_chunks += p["n_chunks"]
    print(f"  product_model actualizado en {len(resolved)} docs / ~{n_chunks} chunks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
