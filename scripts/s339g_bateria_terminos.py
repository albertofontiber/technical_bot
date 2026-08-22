#!/usr/bin/env python3
"""s339g — batería de consultas DERIVADA de los términos que el lote muta.

El hueco que señalaron los dos revisores. Seam-1 y el censo del gate miden sobre el
vocabulario OBSERVADO: 52 gold + 138 consultas reales. Ninguna menciona los términos
nuevos, así que «0 pérdidas / 0 detecciones nuevas» es no-regresión sobre lo que ya se
preguntaba — **no** evidencia de que lo nuevo se comporte bien. Vacuidad, no seguridad.

Esto construye el vocabulario que falta, a partir del propio lote:
  · **POSITIVO** — se pregunta por cada canónico/alias nuevo. Debe detectarse y resolver
    al id que Alberto adjudicó. Si no, la adjudicación no llegó al bot.
  · **NEGATIVO CONTEXTUAL** — el mismo token en un uso que NO es el producto. El caso que
    obligó a esto: «nas» es preposición en portugués («insira os condutores nas portas»),
    y `NAS` es el único término que la huella marcó ALTO. Un disparo aquí es un falso
    positivo que envenena el retrieval.

No decide: mide y lista. Read-only sobre el catálogo simulado.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("CHUNKS_TABLE", "chunks_v2")
os.environ["IDENTITY_RESOLVE_POLICY"] = "replace"   # el brazo de PRODUCCIÓN
os.environ["IDENTITY_RESOLVE"] = "on"

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

from src.rag import catalog_resolver as R                                  # noqa: E402
from src.rag import catalog_store as cs                                    # noqa: E402
from scripts.s324_lote_firmado_writer import aplicar_plan                  # noqa: E402

PLAN = RAIZ / "evals" / "s339e_plan.json"
SALIDA = RAIZ / "evals" / "s339g_bateria.json"

# Negativos CONTEXTUALES: el token en un uso que no es el producto. Cada uno con su razón,
# porque un negativo sin razón es ruido que nadie sabe re-juzgar después.
NEGATIVOS = [
    ("Insira os condutores eléctricos nas respectivas portas de entrada de cabos",
     "«nas» es preposición portuguesa (em+as); aparece literal en el corpus"),
    ("¿Las sirenas van montadas nas paredes o en el techo?",
     "«nas» portugués intercalado en consulta española, que es como llegaría"),
    ("Necesito conectar el equipo a un NAS de red para guardar los históricos",
     "«NAS» informático (Network Attached Storage), homónimo real y plausible en PCI"),
    ("¿Qué pantalla LCD lleva la radio FM/AM del panel?",
     "«FM/AM LCD» — el falso positivo real que frenó AM-LCD en el filtro R19"),
    ("¿Cuántas zonas tiene la serie 800 de otro fabricante cualquiera?",
     "«serie 800» genérico: Serie-800 quedó BLOQUEADA, no debe detectarse como producto"),
]


def resuelve_con(catalog_dir: Path, consultas: list[str]) -> dict[str, dict]:
    orig = cs.load
    try:
        cs.load = lambda *a, **k: orig(catalog_dir)
        R._loaded = False
        R._pattern = None
        R._build()
        return {q: {"detected": R.resolve_query(q)["detected"],
                    "ids": sorted(R.resolve_query(q).get("ids") or [])} for q in consultas}
    finally:
        cs.load = orig
        R._loaded = False
        R._pattern = None


def main() -> int:
    plan = json.loads(PLAN.read_text("utf-8"))
    cat = cs.load()

    # POSITIVOS: un canónico o alias por cada fila que el lote hace consumible.
    positivos: list[tuple[str, str, str]] = []          # (consulta, término, id esperado)
    for a in plan["products_altas"]:
        positivos.append((f"¿Qué es el {a['row']['canonical_model']} y cómo se instala?",
                          a["row"]["canonical_model"], a["row"]["id"]))
    for c in plan["products_confirmar"]:
        positivos.append((f"¿Qué es el {c['canonical_model']} y cómo se instala?",
                          c["canonical_model"], c["id"]))
    for al in plan.get("aliases_altas", []):
        positivos.append((f"Información sobre {al['alias']}", al["alias"], al["id"]))

    consultas = [q for q, _, _ in positivos] + [q for q, _ in NEGATIVOS]

    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp)
        aplicar_plan(plan, dst, cs.CATALOG_DIR)
        antes = resuelve_con(cs.CATALOG_DIR, consultas)
        despues = resuelve_con(dst, consultas)
        cat_d = cs.load(dst)

    fallos_pos, ok_pos = [], []
    for q, term, pid in positivos:
        det = despues[q]["detected"]
        casa = any(cs.norm_token(d) == cs.norm_token(term) for d in det)
        destino = cat_d.follow_redirect(pid)
        fila = {"consulta": q, "termino": term, "id": pid,
                "detected": det, "resuelve_a": destino}
        (ok_pos if casa else fallos_pos).append(fila)

    fallos_neg, ok_neg = [], []
    for q, razon in NEGATIVOS:
        nuevos = [d for d in despues[q]["detected"] if d not in antes[q]["detected"]]
        fila = {"consulta": q, "razon": razon, "antes": antes[q]["detected"],
                "despues": despues[q]["detected"], "nuevos": nuevos}
        (fallos_neg if nuevos else ok_neg).append(fila)

    res = {"positivos_ok": len(ok_pos), "positivos_fallo": fallos_pos,
           "negativos_ok": len(ok_neg), "negativos_fallo": fallos_neg}
    SALIDA.write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")

    print(f"POSITIVOS  {len(ok_pos)}/{len(positivos)} detectan su término")
    for f in fallos_pos:
        print(f"   ✗ «{f['termino']}» no se detecta · detected={f['detected']}")
    print(f"NEGATIVOS  {len(ok_neg)}/{len(NEGATIVOS)} no disparan nada nuevo")
    for f in fallos_neg:
        print(f"   ✗ dispara {f['nuevos']} en: «{f['consulta'][:64]}»\n       ({f['razon']})")
    print(f"\n→ {SALIDA.relative_to(RAIZ)}")
    return 0 if not fallos_pos and not fallos_neg else 1


if __name__ == "__main__":
    raise SystemExit(main())
