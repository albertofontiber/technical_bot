#!/usr/bin/env python3
"""s334 — SONDA DEL SEAM 1: ¿el lote cambia la LISTA DE MODELOS de alguna consulta?

EL HUECO DEL GATE, y por qué importa. El censo de `s324_lote_firmado_writer.py`
mide el detector, `allowed_sources` y los ids de las 51 gold. No mide **`models`**,
que es la otra mitad del seam 1 — y `models` es lo que alimenta
`_filter_to_query_models`, el filtro que SÍ estrecha el pool de chunks.

Y en producción el brazo es **`IDENTITY_RESOLVE_POLICY=replace`** (perfil C1,
fail-fast en `release_profiles.py`), no `add`. Bajo `replace`, resolver un token
lo RETIRA de `models` y pone el canónico en su lugar. Ése es exactamente el
mecanismo con el que LEVER2 regresó hp009 (DEC-091b): quitar el token paraguas
vetó los genéricos correctos. Un lote que promueve 89 productos puede reproducir
ese mecanismo sin que el gate lo vea, porque el gate mira `allowed_sources` —que
sólo AÑADE (unión-protectora, `retriever.py:2369`)— y no `models`, que resta.

QUÉ MIDE. Para cada consulta (51 gold + el tráfico real), calcula
`apply_to_models(extract_product_models(q), resolve_query(q))` con el catálogo de
ANTES y con el de DESPUÉS, bajo la política de producción, y reporta:
  · **PIERDE** — un modelo que estaba en `models` y ya no está  ← el riesgo
  · GANA      — un modelo nuevo (expansión: es lo que se busca)
No decide: mide y lista, para que el dúo tenga el dato delante.

Uso:  python scripts/s334_huerfanos_seam1.py --plan evals/s334_..._plan.json
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
# El brazo de PRODUCCIÓN. Sin esto se mediría `add`, que por construcción no resta
# y daría un «0 pérdidas» tranquilizador y falso (bias #51: validar el número sin
# validar su definición).
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"
os.environ["IDENTITY_RESOLVE"] = "on"

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
sys.path.insert(0, str(ROOT))
from src.rag import catalog_store as cs                            # noqa: E402
from src.rag import catalog_resolver as R                          # noqa: E402
from src.rag.catalog_store import CATALOG_DIR, FILES               # noqa: E402
from src.rag.retriever import extract_product_models               # noqa: E402


def modelos_con(catalog_dir: Path, consultas: list[str]) -> dict[str, list[str]]:
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)
        R._loaded = False
        R._pattern = None
        R._build()
        out = {}
        for q in consultas:
            base = extract_product_models(q)
            out[q] = R.apply_to_models(base, R.resolve_query(q))
        return out
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None


def main() -> int:
    plan_path = Path(sys.argv[sys.argv.index("--plan") + 1])
    plan = json.loads(plan_path.read_text("utf-8"))
    ids = {c["id"] for c in plan["products_confirmar"]}

    golds = [g["question"] for g in yaml.safe_load(
        (ROOT / "evals/gold_answers_v1.yaml").read_text("utf-8"))]
    try:
        from src.http_pool import abierto
        from scripts.s324_lib import consultas_reales
        with abierto(timeout=30.0) as c:
            reales = consultas_reales(c)
    except Exception as e:                                          # noqa: BLE001
        print(f"  (sin tráfico real: {e})")
        reales = []
    consultas = list(dict.fromkeys(golds + list(reales)))
    print(f"consultas: {len(golds)} gold + {len(reales)} reales = {len(consultas)} únicas")
    print(f"política: {os.environ['IDENTITY_RESOLVE_POLICY']}  ·  ids del lote: {len(ids)}")

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # El «después» lo construye EL MISMO CÓDIGO que aplicará el gate
        # (`aplicar_plan`), no una copia mía del efecto. Con sólo `candidate=False`
        # esta sonda se perdería los `products_redirect`, los `doc_map_altas` y los
        # `aliases_altas` del plan — es decir, mediría un plan que no es el que se
        # va a escribir. (s334b: el plan v2 lleva las cuatro cosas.)
        from scripts.s324_lote_firmado_writer import aplicar_plan
        aplicar_plan(plan, d, CATALOG_DIR)
        antes = modelos_con(CATALOG_DIR, consultas)
        despues = modelos_con(d, consultas)

    pierde, gana = {}, {}
    for q in consultas:
        a, b = antes[q], despues[q]
        na, nb = {cs.norm_token(x) for x in a}, {cs.norm_token(x) for x in b}
        if na - nb:
            pierde[q] = {"antes": a, "despues": b, "perdidos": sorted(na - nb)}
        if nb - na:
            gana[q] = {"antes": a, "despues": b, "nuevos": sorted(nb - na)}

    print(f"\n=== SEAM 1 (models) ===")
    print(f"  consultas que PIERDEN algún modelo ... {len(pierde)}   ← el riesgo")
    for q, v in list(pierde.items())[:10]:
        print(f"     «{q[:70]}»\n        {v['antes']} → {v['despues']}  (pierde {v['perdidos']})")
    print(f"  consultas que GANAN algún modelo ..... {len(gana)}")
    for q, v in list(gana.items())[:6]:
        print(f"     «{q[:70]}»  +{v['nuevos']}")

    salida = plan_path.with_name(plan_path.stem.replace("_plan", "") + "_seam1.json")
    salida.write_text(json.dumps(
        {"que_es": "Sonda del seam 1 (models) bajo la política de PRODUCCIÓN (replace): "
                   "lo que el censo del gate no mira. NADA aplicado.",
         "politica": os.environ["IDENTITY_RESOLVE_POLICY"],
         "n_consultas": len(consultas), "n_gold": len(golds), "n_reales": len(reales),
         "pierden": pierde, "ganan": gana}, ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
