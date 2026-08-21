#!/usr/bin/env python3
"""s334c — plan del LOTE DE HIGIENE de `aliases.jsonl` (TECH_DEBT #99).

Convierte el censo (`s334c_higiene_alias.py`) en `aliases_quitar` para el gate de
s324. Es el prerrequisito que el dúo r43 puso delante del lote de huérfanos: su
trigger dice «pasada de higiene ANTES del siguiente lote grande» cuando uno active
más de 20 alias, y el de huérfanos activa 85 hasta en su versión más conservadora.

QUÉ SALE Y QUÉ NO. Sale lo que el censo marca `GENERICO`, y sólo por una de dos
razones MEDIDAS: se dispersa por el corpus (≥25 documentos con frontera de palabra
o ≥3 fabricantes) o es una DESCRIPCIÓN (ningún token con forma de modelo y ninguna
palabra propia). Las señales mecánicas —código de edición, cadena de versión,
frase con artículo— se declaran en el recibo pero **no retiran solas**: son
sospechas, y una sospecha no es una medida.

LO QUE ESTE LOTE **NO** HACE, y es deliberado:
  · No toca productos. Ni promueve, ni retira, ni redirige.
  · No decide a QUÉ producto debería apuntar un alias mal atribuido. El caso que
    dio el dúo —«1 Relay Module» y «2 Relay Module» apuntando LAS DOS a
    `unresolved:mad-412` existiendo `mad-422`, y «Single Input Unit» y «Double
    Input Unit» LAS DOS a `unresolved:mad-402`— se resuelve **retirando las
    cuatro**, no repartiéndolas: cuál es cuál pide el catálogo del fabricante y
    eso es adjudicación (R8).

Uso:  python scripts/s334c_higiene_plan.py [--salida X]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENSO = ROOT / "evals/s334c_higiene_alias_v1.json"
DESTINO = ROOT / "evals/s334c_higiene_alias_plan.json"


def main() -> int:
    destino = (Path(sys.argv[sys.argv.index("--salida") + 1])
               if "--salida" in sys.argv else DESTINO)
    censo = json.loads(CENSO.read_text("utf-8"))
    filas = censo["filas"]
    if censo["resumen"]["examinados"] < 1000:
        print(f"AVISO: el censo sólo examinó {censo['resumen']['examinados']} alias — "
              f"parece un smoke, no la pasada completa. Se genera igual, pero el lote "
              f"NO debe aplicarse con un censo parcial.")

    quitar, motivos = [], Counter()
    for f in filas:
        if f["veredicto"] != "GENERICO":
            continue
        if f["docs_frontera"] >= censo["umbrales"]["docs"]:
            razon = (f"se reparte por el corpus: aparece con FRONTERA DE PALABRA en "
                     f"{f['docs_frontera']} documentos distintos")
            motivos["dispersion-corpus"] += 1
        elif f["n_marcas"] >= censo["umbrales"]["marcas"]:
            razon = (f"aparece en documentos de {f['n_marcas']} fabricantes "
                     f"({', '.join(f['marcas'][:4])}): identifica una categoría, no un producto")
            motivos["varias-marcas"] += 1
        else:
            razon = ("es una DESCRIPCIÓN, no un nombre: ningún token con forma de modelo "
                     "(letras y dígitos juntos) y ninguna palabra propia — sólo vocabulario "
                     "de categoría, que es de cualquier fabricante")
            motivos["descripcion"] += 1
        if f["senales"]:
            razon += f" · señales: {', '.join(f['senales'])}"
        quitar.append({"alias": f["alias"], "id": f["id"],
                       "motivo": f"s334c higiene (TECH_DEBT #99): {razon}"})

    plan = {
        "que_es": "s334c — lote de HIGIENE de aliases.jsonl (TECH_DEBT #99). Sólo "
                  "`aliases_quitar`: no toca productos, ni doc_map, ni la DB.",
        "prerrequisito_de": "el lote de manuales huérfanos (s334b), que el dúo r43 bloqueó "
                            "hasta que esta pasada exista.",
        "products_altas": [], "products_confirmar": [], "products_retirar": [],
        "products_redirect": [], "aliases_altas": [], "aliases_quitar": quitar,
        "umbrellas_altas": [], "doc_map_altas": [], "doc_map_modificaciones": [],
        "retags_db": [], "no_aplicar": [], "gaps": [],
        "perdidas_de_fuente_adjudicadas": [],
        "censo": {"examinados": censo["resumen"]["examinados"],
                  "umbrales": censo["umbrales"], "motivos": dict(motivos)},
    }
    destino.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")
    print(f"alias a retirar: {len(quitar)}  ·  motivos: {dict(motivos)}")
    for q in quitar[:15]:
        print(f"   {q['alias'][:44]:46s} → {q['id']}")
    if len(quitar) > 15:
        print(f"   … y {len(quitar) - 15} más")
    print(f"\n→ {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
