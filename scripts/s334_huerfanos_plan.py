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

#: El lote 1 son TODOS los fabricantes menos notifier: radio pequeño, para probar
#: la maquinaria de punta a punta antes del lote grande. El criterio no es «los
#: fáciles»: es acotar el rollback.
ORDEN = {"pequenos": lambda m: m != "notifier", "notifier": lambda m: m == "notifier"}

#: FUERA por el dúo r42 (Sol xhigh + Fable 5). Los 7 pasaban G4 —desbloquean su
#: manual— y aun así no entran: G4 mide que el manual LLEGUE, no que la fila sea
#: un producto ni que no se pierda nada por el camino. Dos clases distintas:
#:
#:  · PRODUCTO-HOOD (Sol #1, Fable #2). «Clase A» sólo prueba que el token está
#:    en el texto con frontera de palabra. No prueba que el documento trate DE él
#:    (R9) ni que sea un producto (R14). Yo había afirmado en la propuesta que
#:    «ninguna fila entra porque parece un modelo»: era falso para estas tres.
#:  · ESTRECHAMIENTO (Fable #3). Promover puede QUITAR el paraguas de `models`
#:    bajo la política de producción (`replace`) y dejar la consulta con menos
#:    fuentes que antes. Es el mecanismo hp009/DEC-091b, medido aquí por primera
#:    vez: mi G4 sólo preguntaba «¿llega su manual?», nunca «¿se pierde otro?».
FUERA = {
    # producto-hood
    "notifier:eia-485": "R14' — EIA-485 es el bus serie (RS-485), no un producto Notifier. "
                        "71 menciones en su doc porque el manual habla del CABLEADO del bus; "
                        "promoverlo secuestraría toda consulta de bus de cualquier fabricante.",
    "notifier:ad-pe": "R2 — «Versión Exd (AD-PE)» es un SUFIJO de variante, no un modelo suelto "
                      "(1 sola mención, dentro de una tabla de versiones). El producto real, "
                      "`notifier:smart-2-exd-ad-pe`, sí entra.",
    "notifier:rhistorico.exe": "R10 se cumple (el software ES producto) pero la GRAFÍA no: el "
                               "producto se llama «Reparación de Históricos»; `RHistorico.exe` es "
                               "su ejecutable dentro de C:\\NOTIFIER\\Util. Renombrar el canónico "
                               "es adjudicación (R8), no promoción.",
    # estrechamiento medido
    "notifier:tg-6000": "ESTRECHA: la consulta pierde el paraguas `TG` y con él los 4 manuales "
                        "genéricos del TG (Introducción/Usuario/Técnico/requisitos del PC). "
                        "4 fuentes → 1. Arreglarlo es una relación de catálogo, no una promoción.",
    "notifier:tg-6000-net": "ESTRECHA igual que `tg-6000`: 4 fuentes → 1.",
    "notifier:tg-notifier": "ESTRECHA igual: pierde los 4 genéricos del paraguas `TG` (gana 9, "
                            "pero la pérdida es de los manuales que responden las consultas TG).",
    "notifier:m710-cz": "ESTRECHA: pierde `M710` de `models` y 2 fuentes (la hoja combinada "
                        "`I56-2005-002 M710 M720 M721 M701` y el conexionado del M710). Gana 4 "
                        "propias, así que el saldo PARECE bueno — pero la regla que aplico a "
                        "`tg-6000` no puede tener excepciones según me convenga el saldo: el "
                        "instrumento marca estrechamiento y sale del lote autónomo.",
    "systemsensor:8100e-faast": "ESTRECHA 14 fuentes → 1 y colapsa `models` de 14 a 2. La "
                                "discriminación puede ser correcta, pero toca la atribución "
                                "FAAST/Xtralis que YA está pendiente de Alberto.",
}

#: Alias que la promoción ACTIVARÍA en el detector y que no son identificadores de
#: producto (Fable #6). No los crea este lote: ya están en `aliases.jsonl`; lo que
#: hace la promoción es encenderlos. Se quita sólo lo indefendible —un código de
#: edición documental—; el resto de higiene de alias va a TECH_DEBT, no aquí.
ALIAS_FUERA = [{"alias": "MU 591 m 2024 a", "id": "detnov:pad-20",
                "motivo": "s334: código de EDICIÓN del documento (MU 591 m 2024 a), no un "
                          "identificador de producto; la promoción lo metía en el detector"}]


def mejores_por_id(detalle: list[dict]) -> dict[str, dict]:
    """Un id puede atestar varios manuales; se queda con su mejor veredicto."""
    rango = {"DESBLOQUEA": 0, "DESBLOQUEA_PERO_ESTRECHA": 1, "YA_ALCANZABLE": 2,
             "DETECTA_SIN_FUENTE": 3, "NI_DETECTA": 4}
    out: dict[str, dict] = {}
    for d in detalle:
        if d["id"] not in out or rango[d["veredicto"]] < rango[out[d["id"]]["veredicto"]]:
            out[d["id"]] = d
    # …salvo el ESTRECHAMIENTO, donde manda el PEOR caso: un id que desbloquea un
    # manual limpiamente y estrecha en otro sigue estrechando. Tomar el mejor
    # veredicto aquí escondería exactamente el daño que el veredicto existe para
    # ver (y sería el «valido el número, no la definición del número» otra vez).
    estrechan = {d["id"] for d in detalle if d["veredicto"] == "DESBLOQUEA_PERO_ESTRECHA"}
    for pid in estrechan:
        out[pid] = next(d for d in detalle
                        if d["id"] == pid and d["veredicto"] == "DESBLOQUEA_PERO_ESTRECHA")
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
        if d["veredicto"] != "DESBLOQUEA" or not filtro(pid.split(":", 1)[0]) or pid in FUERA:
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
                    "G4 — dentro SÓLO si resolve_query pasa de no traer su manual a traerlo",
                    "dúo r42 — fuera si la fila no es un PRODUCTO (R9/R14) o si promoverla "
                    "ESTRECHA las fuentes de su propia consulta (mecanismo hp009/DEC-091b)"],
        "fuera_por_el_duo": {k: v for k, v in FUERA.items() if filtro(k.split(":", 1)[0])},
        "products_altas": [],
        "products_confirmar": confirmar,
        "products_retirar": [],
        "products_redirect": [],
        "aliases_altas": [],
        "aliases_quitar": [a for a in ALIAS_FUERA if filtro(a["id"].split(":", 1)[0])],
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
