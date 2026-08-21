#!/usr/bin/env python3
"""s334 — genera el PLAN del lote firmado que desbloquea manuales huérfanos.

QUÉ ENTRA EN EL LOTE, y por qué sólo eso. La evidencia (`…evidencia_v1.json`)
propuso 118 ids de clase A; el filtro de riesgos declarados dejó 110; y la
VERIFICACIÓN con el resolver real (`…verificacion_v1.json`, guarda G4) dejó **89**:
los únicos para los que se comprobó, ejecutando `resolve_query` antes y después,
que la consulta por el nombre del modelo NO traía su manual y después SÍ.

Los 21 descartados NO son ruido, son tres fallos con nombre —y ninguno se veía
desde el texto del documento, que es lo único que miraba la evidencia:

  **H · homónimo abierto** (10). El token existe en DOS namespaces
  (`morley:sp-200` / `notifier:sp-200`) y su fila de `homonyms.jsonl` está
  `candidate: true, politica: fail-open`. El resolver devuelve `expand: False` e
  `ids: []`, así que promover el producto deja el término EN el detector y el
  manual FUERA. Decidir si el SP-200 de Morley y el de Notifier son el mismo
  producto rebrandeado es adjudicación (R8), no mecánica.

  **G · gemelo** (6). El token ya resuelve a OTRO id: `ID-3000`→`notifier:id3000`,
  `ST.PL4+`→`notifier:stpl4`, y `TG-1020`→**`desico:tg-1020`**, que ni siquiera es
  la misma marca. Promover el candidate no mueve nada porque el detector nunca
  llega a él. Es el mismo patrón de gemelos que DEC-173 encontró en `chunk_index`,
  ahora en el espacio de ids.

  **N · no detectable** (5). `00051`, `03382`… son referencias puramente
  numéricas, y el detector excluye los tokens digit-only a propósito; `EEV(2)`
  lleva paréntesis y `detect()` devuelve lista vacía. Promoverlos es inerte.

LO QUE ESTE SCRIPT NO DECIDE. No escribe en el catálogo: produce el fichero de
plan que consume `s324_lote_firmado_writer.py`, que hace dry-run + censo del radio
de explosión y exige PASS antes de `--aplicar`.

Uso:  python scripts/s334_huerfanos_plan.py --lote pequenos|notifier [--salida X]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIF = ROOT / "evals/s334_huerfanos_verificacion_v1.json"
EVID = ROOT / "evals/s334_huerfanos_evidencia_v1.json"
#: Ruta PROPIA: el gate acepta `--plan`, así que no se pisa el plan histórico de
#: s324 (que es el recibo de un lote ya aplicado, no un borrador reutilizable).
DESTINO = ROOT / "evals/s334_huerfanos_lote_{lote}_plan.json"

#: El lote 1 son TODOS los fabricantes menos notifier: 28 ids con radio pequeño,
#: para probar la maquinaria de punta a punta antes del lote grande (61 de
#: notifier). El criterio no es «los fáciles»: es acotar el rollback.
ORDEN = {"pequenos": lambda m: m != "notifier", "notifier": lambda m: m == "notifier"}


def mejores_por_id(detalle: list[dict]) -> dict[str, dict]:
    """Un id puede atestar varios manuales; se queda con su mejor veredicto."""
    rango = {"DESBLOQUEA": 0, "YA_ALCANZABLE": 1, "DETECTA_SIN_FUENTE": 2, "NI_DETECTA": 3}
    out: dict[str, dict] = {}
    for d in detalle:
        if d["id"] not in out or rango[d["veredicto"]] < rango[out[d["id"]]["veredicto"]]:
            out[d["id"]] = d
    return out


def main() -> int:
    if "--lote" not in sys.argv:
        raise SystemExit("falta --lote pequenos|notifier")
    lote = sys.argv[sys.argv.index("--lote") + 1]
    if lote not in ORDEN:
        raise SystemExit(f"--lote debe ser uno de {sorted(ORDEN)}")
    destino = (Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv
               else Path(str(DESTINO).format(lote=lote)))

    verif = json.loads(VERIF.read_text("utf-8"))
    evid = json.loads(EVID.read_text("utf-8"))
    cita_de = {it["id"]: it for l in evid["lotes"].values() for it in l["ids"]}

    mejores = mejores_por_id(verif["detalle"])
    filtro = ORDEN[lote]
    confirmar = []
    for pid, d in sorted(mejores.items()):
        if d["veredicto"] != "DESBLOQUEA" or not filtro(pid.split(":", 1)[0]):
            continue
        it = cita_de.get(pid, {})
        cita = (it.get("cita") or "").replace("\n", " ")[:150]
        confirmar.append({
            "id": pid,
            "canonical_model": d["canonico"],
            # La provenance lleva la CITA: es lo que hace la fila auditable a ojo
            # dentro del propio catálogo, sin volver a este fichero.
            "provenance_add": (f"s334 huérfano-desbloqueado: su manual no era alcanzable por "
                               f"nombre de modelo y ahora sí (G4 verificado con resolve_query). "
                               f"Cita en su propio doc: «{cita}»"),
            "_manuales": d.get("fuentes_del_id", []),
            "_menciones_en_su_doc": it.get("menciones_en_su_doc"),
        })

    plan = {
        "que_es": f"s334 lote «{lote}»: promueve candidates cuya promoción DESBLOQUEA un manual "
                  f"huérfano, verificado con el resolver real (G4). Sólo `products_confirmar`: "
                  f"no da altas, no retira, no toca doc_map ni la DB.",
        "guardas": ["A/R4 — cita verificada con frontera de palabra en su propio documento",
                    "H — fuera si su token tiene homónimo abierto (rebrand: adjudicación, R8)",
                    "G — fuera si su token ya resuelve a otro id (gemelo)",
                    "N — fuera si el detector no puede verlo (digit-only, paréntesis)",
                    "G4 — dentro SÓLO si resolve_query pasa de no traer su manual a traerlo"],
        "products_altas": [],
        "products_confirmar": confirmar,
        "products_retirar": [],
        "products_redirect": [],
        "aliases_altas": [],
        "aliases_quitar": [],
        "umbrellas_altas": [],
        "doc_map_altas": [],
        "doc_map_modificaciones": [],
        "retags_db": [],
        "no_aplicar": [],
        "gaps": [],
        "perdidas_de_fuente_adjudicadas": [],
    }
    destino.write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")
    print(f"lote «{lote}»: {len(confirmar)} ids a confirmar")
    for c in confirmar[:6]:
        print(f"   {c['id']:32s} {c['canonical_model']!r}")
    if len(confirmar) > 6:
        print(f"   … y {len(confirmar) - 6} más")
    print(f"\n→ {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
