#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
s322_packets_v2.py — ENSAMBLADOR determinista de los tres packets de adjudicación v2.

QUÉ HACE
========
Lee los SIETE recibos JSON que produjeron las pasadas hermanas de s322f/s322g y
escribe tres markdown en `evals/`:

  * evals/s320_e1_packet_adjudicacion_v2.md   (colisiones + tier B + candidates + pm sucio)
  * evals/s320_e1b_packet_adjudicacion_v2.md  (confirmar + revisar)
  * evals/s320_e2_packet_adjudicacion_v2.md   (altas del detector)

POR QUÉ ES DETERMINISTA (SIN LLM)
=================================
El juicio ya está hecho y pagado en los recibos: cada fila trae su veredicto, su
confianza, su cita verificada a texto completo y sus gates. Volver a llamar a un
modelo aquí sólo podría INTRODUCIR variación (el muestreo sin `temperature` no es
determinista) sobre un juicio ya cerrado. Este script sólo REORDENA y RECORTA lo
que ya está escrito. Consecuencia práctica: es idempotente y re-ejecutable, y su
diff contra el recibo es auditable línea a línea.

POR QUÉ NO ESCRIBE NADA MÁS QUE MARKDOWN
========================================
Los packets son PROPUESTAS para que Alberto adjudique. Este script no toca
`data/catalog/*.jsonl`, ni Supabase, ni `data/model_catalog.json`. Sólo abre los
recibos en modo lectura y crea/actualiza los tres .md.

INVARIANTE DE INTEGRIDAD (el control de este script)
====================================================
Los conteos del encabezado NO se escriben a mano: se leen de los recibos, y al
final se comparan contra las filas REALMENTE renderizadas (un contador por
sección que se incrementa en el mismo sitio donde se emite la fila). Si no
cuadran, el script ABORTA sin escribir. Un packet cuyo encabezado miente es peor
que no tener packet: destruye la confianza en el resto de las cifras.

Uso:  python scripts/s322_packets_v2.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"

UTC = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# ---------------------------------------------------------------------------
# 1. RECIBOS DE ENTRADA + sus totales DECLARADOS por la pasada que los produjo.
#    Los totales van aquí para detectar DRIFT: si un recibo se regenera y cambia
#    de tamaño, el ensamblador se entera en vez de escribir un packet obsoleto.
# ---------------------------------------------------------------------------
RECIBOS: "OrderedDict[str, dict]" = OrderedDict(
    [
        ("colisiones", {"path": EVALS / "s322f_e1_colisiones_adjudicacion_v1.json",
                        "total": 49, "bloque": 49, "individual": 0}),
        ("altas", {"path": EVALS / "s322f_e2_altas_split_v1.json",
                   "total": 1235, "bloque": 562, "individual": 669}),
        ("tierb", {"path": EVALS / "s322f_e1s2_tierb_docmap_v1.json",
                   "total": 67, "bloque": 42, "individual": 13}),
        ("candidates", {"path": EVALS / "s322g_e1_candidatos_triage_v1.json",
                        "total": 133, "bloque": 50, "individual": 83}),
        ("revisar", {"path": EVALS / "s322_e1b_revisar_qa_v1.json",
                     "total": 261, "bloque": 148, "individual": 113}),
        ("confirmar", {"path": EVALS / "s322f_e1b_confirmar_encoger_v1.json",
                       "total": 359, "bloque": 327, "individual": 32}),
        ("pm_sucio", {"path": EVALS / "s322g_e1_pm_sucio_v1.json",
                      "total": 4, "bloque": 3, "individual": 1}),
    ]
)

SALIDAS = {
    "e1": EVALS / "s320_e1_packet_adjudicacion_v2.md",
    "e1b": EVALS / "s320_e1b_packet_adjudicacion_v2.md",
    "e2": EVALS / "s320_e2_packet_adjudicacion_v2.md",
}

# Los packets v1 a los que cada v2 SUPERSEDE (se citan en la cabecera para que
# quede claro cuál hay que dejar de mirar; no se borran ni se tocan).
V1 = {
    "e1": "evals/s320_e1_packet_adjudicacion_v1.md",
    "e1b": "evals/s320_e1_packet_adjudicacion_v1.md (§5 «confirmar»/«revisar» del E1b)",
    "e2": "evals/s320_e2_packet_adjudicacion_v1.md",
}

# Umbral blando de legibilidad: por encima de esto una sección se agrupa en
# lotes y apunta al recibo para el detalle fila a fila (regla del encargo).
UMBRAL_LINEAS_SECCION = 400

AUSENTE = "(el recibo no trae este campo)"


# ---------------------------------------------------------------------------
# 2. UTILIDADES DE RECORTE
#    Todo lo que se imprime pasa por aquí. `corta()` normaliza espacios porque
#    las citas del corpus vienen con saltos de línea y tablas markdown dentro:
#    sin normalizar, una sola cita rompe la lectura de un packet entero.
# ---------------------------------------------------------------------------
def corta(txt: Any, n: int = 110) -> str:
    if txt is None or txt == "":
        return AUSENTE
    s = re.sub(r"\s+", " ", str(txt)).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def cita(txt: Any, n: int = 110) -> str:
    """Cita entrecomillada al estilo del packet que Alberto ya lee."""
    if not txt:
        return "sin cita en el recibo"
    return "«" + corta(txt, n) + "»"


def id8(uuid: Any) -> str:
    """Prefijo de UUID: suficiente para casar a ojo con el recibo, sin ruido."""
    return (str(uuid)[:8] + "…") if uuid else AUSENTE


def dic(x: Any) -> dict:
    """
    Acceso defensivo a un sub-objeto del recibo.

    POR QUÉ: varias filas traen `llm: null` (p.ej. las que se resolvieron sin
    juez, o cuya llamada falló). Un `.get("llm", {})` NO protege de eso: el
    default sólo actúa si la clave falta, no si vale null. Sin este envoltorio
    el ensamblador reventaba a mitad del E1b. La regla del encargo —«si un
    recibo no trae un campo, dilo en vez de rellenarlo»— se cumple porque el
    dict vacío hace que cada campo se imprima como AUSENTE.
    """
    return x if isinstance(x, dict) else {}


def ids_fmt(ids: Iterable[Any] | None, maximo: int = 6) -> str:
    ids = list(ids or [])
    if not ids:
        return "—"
    if len(ids) <= maximo:
        return ", ".join("`%s`" % i for i in ids)
    return ", ".join("`%s`" % i for i in ids[:maximo]) + " …(+%d)" % (len(ids) - maximo)


def envuelve(items: list[str], ancho: int = 108, sangria: str = "      ") -> list[str]:
    """
    Empaqueta muchos items cortos en pocas líneas.

    POR QUÉ: los lotes grandes (518 altas sin chunks, 197 confirmaciones
    deterministas) son auditables como INVENTARIO — Alberto quiere ver que su
    modelo está o no está en la lista — pero una línea por fila los volvería
    ilegibles. Envolviendo, cada término sigue VISIBLE y verificable con Ctrl-F
    sin gastar 500 líneas.
    """
    out, cur = [], ""
    for it in items:
        cand = it if not cur else cur + " · " + it
        if len(cand) > ancho and cur:
            out.append(sangria + cur)
            cur = it
        else:
            cur = cand
    if cur:
        out.append(sangria + cur)
    return out


def plural(n: Any, singular: str, plural_: str | None = None) -> str:
    """«1 chunk» / «7 chunks»: concordancia en las cifras que se leen en cada línea."""
    try:
        uno = int(n) == 1
    except (TypeError, ValueError):
        uno = False
    return "%s %s" % (n, singular if uno else (plural_ or singular + "s"))


def marca_de(idc: str) -> str:
    """Prefijo de marca de un id gobernado `marca:modelo`."""
    return idc.split(":", 1)[0] if ":" in str(idc) else "(sin marca)"


# ---------------------------------------------------------------------------
# 3. CONSTRUCTOR DE PACKET
#    Acumula líneas y cuenta FILAS por sección en el mismo punto donde se emiten.
#    Ese contador es el que se contrasta al final contra los recibos.
# ---------------------------------------------------------------------------
class Packet:
    def __init__(self, clave: str, titulo: str) -> None:
        self.clave = clave
        self.titulo = titulo
        self.lineas: list[str] = []
        self.filas: Counter = Counter()          # filas renderizadas por sección
        self.casillas: Counter = Counter()       # casillas `- [ ]` por sección
        self.seccion_actual = "?"
        self._marca_linea: dict[str, int] = {}   # nº de línea al abrir sección

    # -- emisión cruda -------------------------------------------------------
    def w(self, txt: str = "") -> None:
        self.lineas.append(txt)

    def abre_seccion(self, clave: str, encabezado: str) -> None:
        self.seccion_actual = clave
        self._marca_linea[clave] = len(self.lineas)
        self.w(encabezado)
        self.w()

    def lineas_de_seccion(self, clave: str) -> int:
        """Cuántas líneas ocupa una sección (para el guardarraíl de legibilidad)."""
        ini = self._marca_linea.get(clave)
        if ini is None:
            return 0
        siguientes = [v for v in self._marca_linea.values() if v > ini]
        fin = min(siguientes) if siguientes else len(self.lineas)
        return fin - ini

    # -- emisión de filas ----------------------------------------------------
    def fila(self, texto: str, extra: list[str] | None = None, casilla: bool = True) -> None:
        """Una FILA = una unidad del recibo. Cuenta para el invariante."""
        self.lineas.append(("- [ ] " if casilla else "- ") + texto)
        for e in extra or []:
            self.lineas.append("      " + e)
        self.filas[self.seccion_actual] += 1
        if casilla:
            self.casillas[self.seccion_actual] += 1

    def lote(self, cabecera: str, items: list[str], n_filas: int,
             pie: list[str] | None = None) -> None:
        """
        Un LOTE = una casilla que cubre n_filas del recibo, con los términos
        listados para poder auditarlos sin abrir el JSON.
        """
        self.lineas.append("- [ ] " + cabecera)
        self.lineas.extend(envuelve(items))
        for p in pie or []:
            self.lineas.append("      " + p)
        self.filas[self.seccion_actual] += n_filas
        self.casillas[self.seccion_actual] += 1

    def total_filas(self, claves: Iterable[str]) -> int:
        return sum(self.filas[k] for k in claves)

    def texto(self) -> str:
        return "\n".join(self.lineas).rstrip() + "\n"


# ---------------------------------------------------------------------------
# 4. CARGA + CHEQUEO DE DRIFT
# ---------------------------------------------------------------------------
def carga() -> dict[str, dict]:
    datos, problemas = {}, []
    for clave, meta in RECIBOS.items():
        p: Path = meta["path"]
        if not p.exists():
            problemas.append("FALTA el recibo %s" % p)
            continue
        datos[clave] = json.loads(p.read_text(encoding="utf-8"))
    if problemas:
        sys.exit("ABORTA:\n  " + "\n  ".join(problemas))
    return datos


def chequea_drift(d: dict[str, dict]) -> list[str]:
    """
    Compara los totales DECLARADOS en el encargo con los que trae cada recibo.
    No aborta por sí solo: devuelve avisos que se estampan en los packets, para
    que un desajuste sea VISIBLE en vez de silencioso.
    """
    avisos: list[str] = []

    def cmp(nombre: str, esperado: int, real: int, etiqueta: str) -> None:
        if esperado != real:
            avisos.append("DRIFT en %s · %s: esperado %d, en el recibo %d"
                          % (nombre, etiqueta, esperado, real))

    cmp("colisiones", 49, len(d["colisiones"]["seccion_0_bloque"]), "bloque")
    cmp("colisiones", 0, len(d["colisiones"]["seccion_1_individual"]), "individual")
    cmp("altas", 562, len(d["altas"]["seccion_0_bloque"]), "bloque")
    cmp("altas", 669, len(d["altas"]["seccion_1_individual"]), "individual")
    cmp("tierb", 42, len(d["tierb"]["seccion_0_bloque"]), "bloque")
    cmp("tierb", 13, len(d["tierb"]["seccion_1_individual"]), "individual")
    cmp("candidates", 50,
        len(d["candidates"]["seccion_0a_alta_en_bloque"]) +
        len(d["candidates"]["seccion_0b_retirar_en_bloque"]), "bloque")
    cmp("candidates", 83, len(d["candidates"]["seccion_1_individual"]), "individual")
    cmp("revisar", 148,
        len(d["revisar"]["secciones"]["0_bloque_confirmar"]) +
        len(d["revisar"]["secciones"]["0_bloque_retirar"]), "bloque")
    cmp("revisar", 113, len(d["revisar"]["secciones"]["1_individual"]), "individual")
    cmp("confirmar", 327, len(d["confirmar"]["detalle"]["bloque"]), "bloque")
    cmp("confirmar", 32, len(d["confirmar"]["detalle"]["individual"]), "individual")
    cmp("pm_sucio", 3, len(d["pm_sucio"]["seccion_0_bloque"]), "bloque")
    cmp("pm_sucio", 1, len(d["pm_sucio"]["seccion_1_individual"]), "individual")
    return avisos


def cabecera_comun(pk: Packet, avisos_drift: list[str]) -> None:
    pk.w("**NADA APLICADO.** Ni catálogo (`data/catalog/*.jsonl`), ni Supabase, ni el")
    pk.w("snapshot del detector (`data/model_catalog.json`). Todo lo de aquí es PROPUESTA:")
    pk.w("marca ✓/✗ y se aplica después por la puerta gobernada, con recibo.")
    pk.w()
    if avisos_drift:
        pk.w("> ⚠ **Aviso de drift entre el encargo y los recibos** (no se ha corregido nada,")
        pk.w("> se declara):")
        for a in avisos_drift:
            pk.w("> - " + a)
        pk.w()


# ===========================================================================
# 5. PACKET E1
# ===========================================================================
def construye_e1(d: dict[str, dict], avisos: list[str]) -> Packet:
    col = d["colisiones"]
    tb = d["tierb"]
    ca = d["candidates"]
    pm = d["pm_sucio"]

    n_col = len(col["seccion_0_bloque"])
    n_tb_b, n_tb_i = len(tb["seccion_0_bloque"]), len(tb["seccion_1_individual"])
    n_tb_fuera = len(tb["seccion_2_fuera_del_packet"])
    n_ca_alta = len(ca["seccion_0a_alta_en_bloque"])
    n_ca_ret = len(ca["seccion_0b_retirar_en_bloque"])
    n_ca_i = len(ca["seccion_1_individual"])
    n_pm_b, n_pm_i = len(pm["seccion_0_bloque"]), len(pm["seccion_1_individual"])

    total = n_col + (n_tb_b + n_tb_i + n_tb_fuera) + (n_ca_alta + n_ca_ret + n_ca_i) + (n_pm_b + n_pm_i)
    bloque = n_col + n_tb_b + n_ca_alta + n_ca_ret + n_pm_b
    individual = n_tb_i + n_ca_i + n_pm_i

    pk = Packet("e1", "E1")
    pk.w("# s320 E1 — Packet de ADJUDICACIÓN **v2 (encogido)** · %s" % UTC)
    pk.w()
    pk.w("**SUPERSEDE a `%s`.**" % V1["e1"])
    pk.w("Aquel packet te pedía **%d casillas** una a una (§1 colisiones, §2 tier B," % total)
    pk.w("§3 candidates, §4 product_model sucio). Cuatro pasadas hermanas han refrescado cada")
    pk.w("fila contra el estado de HOY, la han juzgado con cita verificada a texto completo y")
    pk.w("la han separado en dos: lo que aguanta un solo «sí», y el residuo real.")
    pk.w()
    pk.w("> ### De **%d casillas** → **%d decisiones**" % (total, individual + 1))
    pk.w("> - **1 sí en bloque** cubre **%d filas** (§0, en 5 sub-bloques por si prefieres" % bloque)
    pk.w(">   asentir por partes).")
    pk.w("> - **%d una a una** (§1) — el residuo con la evidencia junta." % individual)
    pk.w("> - **%d ya no aplican** (§2): se cayeron solas al refrescar. No decides nada." % n_tb_fuera)
    pk.w()
    cabecera_comun(pk, avisos)

    # ---------------------- §0 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (%d)" % bloque)
    pk.w()
    pk.w("Criterio, idéntico en las cuatro pasadas: **veredicto claro + confianza alta +")
    pk.w("cita verificada contra el CONTENIDO COMPLETO del documento (≤200 chars, espacios")
    pk.w("normalizados) + sin ambigüedad estructural**. Una confianza alta cuya cita no")
    pk.w("verifica se degradó a media y cayó a la §1: por eso el bloque es asentible de una vez.")
    pk.w()

    # §0.A — colisiones
    pk.abre_seccion(
        "0A", "### §0.A — Colisiones de identidad: **repuntar `doc_map`** (%d)" % n_col)
    cm = dic(col.get("consecuencia_medida"))
    tot_col = dic(col.get("totales"))
    pk.w("Las %d son la MISMA clase: `%s`. La fila del mapa apunta a un `document_id`"
         % (n_col, ", ".join(dic(col.get("por_clase")).keys()) or AUSENTE))
    pk.w("**retirado y con CERO filas** en `chunks_v2`/`chunks`/`enunciados`/`visual_assets`/")
    pk.w("`group_members`, su `sha` es pseudo-backfill y su nota apunta al id vivo: es una ficha")
    pk.w("fantasma de s65, no un duplicado real. **No hay supersede que hacer** (una ficha de 0")
    pk.w("chunks nunca fue una revisión) y **`documents` no se toca**.")
    pk.w()
    pk.w("- Impacto MEDIDO (no teorizado): la atestación del anexo `must_preserve` (join por")
    pk.w("  `document_id`) **falla hoy en %s docs** con el id servido y **atestaría con el id"
         % cm.get("docs_donde_la_atestacion_falla_con_el_id_servido", AUSENTE))
    pk.w("  fantasma en %s**. `allowed_sources`: %s"
         % (cm.get("docs_donde_atestaria_con_el_id_fantasma", AUSENTE),
            corta(cm.get("seam_allowed_sources"), 150)))
    pk.w("- Entradas del catálogo afectadas: **%s**." % tot_col.get("entries_del_catalogo_afectadas", AUSENTE))
    pk.w("- Acción por fila: `doc_map` → repuntar `document_id` (mapa → actual). `source_file` intacto.")
    pk.w()

    # Los 9 gates, el seam y la propuesta son IDÉNTICOS en las 49 filas. En vez
    # de repetir ese texto 49 veces (ilegible, y esconde lo único que cambia de
    # fila a fila: el par de ids), se factoriza al preámbulo. La uniformidad se
    # COMPRUEBA aquí, no se da por supuesta: si un recibo futuro trae filas
    # heterogéneas, el script vuelve solo al formato largo por fila.
    filas_col = col["seccion_0_bloque"]
    firmas_gate = {json.dumps(dic(r.get("gates")), sort_keys=True) for r in filas_col}
    firmas_seam = {json.dumps({k: v for k, v in dic(r.get("seam_atestacion")).items()
                               if k != "modelo_sonda"}, sort_keys=True) for r in filas_col}
    firmas_prop = {json.dumps(dic(r.get("propuesta")), sort_keys=True) for r in filas_col}
    uniforme = len(firmas_gate) == 1 and len(firmas_seam) == 1 and len(firmas_prop) == 1

    if uniforme:
        g0 = dic(filas_col[0].get("gates"))
        s0 = dic(filas_col[0].get("seam_atestacion"))
        pk.w("**Los 9 gates dan lo mismo en las %d filas** (comprobado al ensamblar, no supuesto),"
             % len(filas_col))
        pk.w("así que se declaran UNA vez en vez de repetirlos en cada línea:")
        pk.w()
        for k, v in sorted(g0.items()):
            pk.w("  - `%s` = **%s**" % (k, v))
        pk.w("  - seam medible en las %d: atesta con el id **fantasma**=%s, con el id"
             % (len(filas_col), s0.get("atesta_con_id_fantasma")))
        pk.w("    **servido**=%s → repuntar arregla la atestación." % s0.get("atesta_con_id_actual"))
        pk.w()
        pk.w("Lo único que cambia por fila es el par de ids y la sonda que lo demuestra:")
        pk.w()
    else:
        pk.w("> ⚠ Las filas NO son homogéneas (%d combinaciones de gates, %d de seam, %d de"
             % (len(firmas_gate), len(firmas_seam), len(firmas_prop)))
        pk.w("> propuesta): cada línea lleva sus gates propios.")
        pk.w()

    por_tier: dict[str, list[dict]] = defaultdict(list)
    for r in filas_col:
        por_tier[str(r.get("tier", "?"))].append(r)
    for tier in sorted(por_tier):
        filas = sorted(por_tier[tier], key=lambda r: str(r.get("source_file", "")))
        pk.w("**%s (%d)**" % (tier, len(filas)))
        pk.w()
        for r in filas:
            g = dic(r.get("gates"))
            seam = dic(r.get("seam_atestacion"))
            sonda = ("sonda `%s`" % seam.get("modelo_sonda")) if seam.get("medible") \
                else "seam no medible en esta fila"
            if uniforme:
                pk.fila("`%s` · %s · mapa %s → actual %s · %s" % (
                    r.get("source_file", AUSENTE),
                    plural(r.get("n_entries_adjudicadas"), "entrada"),
                    id8(dic(r.get("fila_mapa")).get("id")),
                    id8(dic(r.get("fila_actual")).get("id")), sonda))
            else:
                pk.fila("`%s` · %s entradas · mapa %s (%s) → actual %s (%s) · %s" % (
                    r.get("source_file", AUSENTE),
                    r.get("n_entries_adjudicadas", AUSENTE),
                    id8(dic(r.get("fila_mapa")).get("id")), g.get("mapa_status"),
                    id8(dic(r.get("fila_actual")).get("id")), g.get("actual_status"), sonda),
                    ["gates: %s" % corta(json.dumps(g, ensure_ascii=False), 200)])
        pk.w()

    # §0.B — tier B doc_map
    pk.abre_seccion(
        "0B", "### §0.B — `doc_map` tier B: **altas de entrada** (%d)" % n_tb_b)
    pk.w("Docs cuyo `product_model` resolvía a varios ids y quedaba ambiguo. Gate de bloque")
    pk.w("(los 7 se cumplen en las %d):" % n_tb_b)
    for c in tb.get("criterio_de_bloque", []):
        pk.w("  %d. %s" % (tb["criterio_de_bloque"].index(c) + 1, c))
    pk.w()
    pk.w("Juez `%s`. Veredictos del lote completo: %s"
         % (tb.get("modelo_juez", AUSENTE),
            ", ".join("%s=%d" % (k, v) for k, v in dic(tb.get("por_veredicto")).items())))
    pk.w()
    for r in sorted(tb["seccion_0_bloque"], key=lambda x: str(x.get("source_file", ""))):
        llm = dic(r.get("llm"))
        oem = dic(r.get("bandera_oem"))
        extra = ["→ **%s** · %s · cita ✓ %s" % (
            llm.get("veredicto", AUSENTE),
            ids_fmt(r.get("ids_propuestos")),
            cita(llm.get("cita")))]
        if oem:
            extra.append("⚑ OEM/reventa: documento de **%s**, ids bajo **%s**" % (
                oem.get("fabricante_del_documento", AUSENTE),
                ", ".join(sorted({marca_de(i) for i in (oem.get("ids_de_otra_marca") or [])})) or AUSENTE))
        if r.get("tokens_sin_id"):
            extra.append("tokens del pm sin id (familia/serie, no se dan de alta): %s"
                         % ", ".join("`%s`" % t for t in r["tokens_sin_id"]))
        pk.fila("`%s` (%s · %s · pm «%s»)" % (
            r.get("source_file", AUSENTE), r.get("manufacturer", AUSENTE),
            plural(r.get("n_chunks"), "chunk"), corta(r.get("pm_doc"), 60)), extra)
    pk.w()

    # §0.C — candidates ALTA
    pk.abre_seccion(
        "0C", "### §0.C — Candidates → **ALTA** (%d)" % n_ca_alta)
    met = dic(ca.get("metodo"))
    pk.w("Altas `candidate` del draft del detector. Muestreo **dirigido** (%s)."
         % corta(met.get("muestreo"), 130))
    pk.w("Señales duras: %s" % corta(met.get("senales_duras"), 150))
    pk.w("Degradación: %s" % corta(met.get("degradacion"), 120))
    pk.w()
    # Una FILA del draft es (id, documento): el mismo id puede llegar desde dos
    # manuales, a veces con grafías distintas (ID²net / ID2NET). Si no se dice,
    # el «sí» parece dar de alta más productos de los que realmente da.
    res_ca = dic(ca.get("resumen"))
    ids_alta = [r.get("id") for r in ca["seccion_0a_alta_en_bloque"]]
    rep_alta = {i: c for i, c in Counter(ids_alta).items() if c > 1}
    pk.w("Ojo al contar: **%d filas → %d ids únicos** (una fila es un par id+documento)."
         % (len(ids_alta), len(set(ids_alta))))
    if rep_alta:
        pk.w("Ids propuestos desde MÁS DE UN documento: %s."
             % ", ".join("`%s`×%d" % (i, c) for i, c in sorted(rep_alta.items())))
        pk.w("No son altas duplicadas: es el mismo producto atestado dos veces.")
    pk.w("En el lote entero (bloque+residuo) el recibo cuenta %s ids únicos sobre %s filas."
         % (res_ca.get("ids_unicos_en_el_draft", AUSENTE), res_ca.get("total", AUSENTE)))
    pk.w()
    for r in sorted(ca["seccion_0a_alta_en_bloque"], key=lambda x: str(x.get("id", ""))):
        llm, sn = dic(r.get("llm")), dic(r.get("senales"))
        md, mg = dic(sn.get("menciones_doc")), dic(sn.get("menciones_muestra_global"))
        pk.fila("`%s` (%s) → **ALTA** · rol %s · doc `%s`" % (
            r.get("id", AUSENTE), r.get("canonical_model", AUSENTE),
            llm.get("rol_en_texto", AUSENTE),
            corta(dic(r.get("documento")).get("source_pdf_filename"), 58)),
            ["menciones estrictas doc %s / global %s en %s · cita %s %s" % (
                md.get("estrictas", "?"), mg.get("estrictas", "?"),
                plural(mg.get("documentos", "?"), "doc"),
                "✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 95))])
    pk.w()

    # §0.D — candidates RETIRAR
    pk.abre_seccion(
        "0D", "### §0.D — Candidates → **RETIRAR** (%d)" % n_ca_ret)
    h = dic(ca.get("hallazgos"))
    pk.w("Términos que el detector propuso como producto y **NO lo son**: son artefactos de")
    pk.w("extracción (código del propio documento, nombre de fabricante, frase técnica). La")
    pk.w("pasada detectó **%s artefactos** sobre **%s ids únicos**; clases: %s."
         % (h.get("artefactos_detectados", AUSENTE), h.get("ids_unicos_afectados", AUSENTE),
            ", ".join("`%s`" % k for k in dic(h.get("por_clase")))))
    pk.w("Retirar = no darlos de alta. Es la mitad barata del sí: quita ruido del detector.")
    pk.w()
    for r in sorted(ca["seccion_0b_retirar_en_bloque"], key=lambda x: str(x.get("id", ""))):
        llm, sn = dic(r.get("llm")), dic(r.get("senales"))
        md = dic(sn.get("menciones_doc"))
        pk.fila("`%s` (%s) → **RETIRAR** · %s / %s · doc `%s`" % (
            r.get("id", AUSENTE), r.get("canonical_model", AUSENTE),
            llm.get("veredicto", AUSENTE), llm.get("rol_en_texto", AUSENTE),
            corta(dic(r.get("documento")).get("source_pdf_filename"), 50)),
            ["estrictas %s · mayúsculas %s · como fragmento %s · cita %s %s" % (
                md.get("estrictas", "?"), md.get("mayusculas", "?"), md.get("como_fragmento", "?"),
                "✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 90)),
             "razón: %s" % corta(llm.get("razon"), 150)])
    pk.w()

    # §0.E — pm sucio
    ver_pm = Counter(str(r.get("veredicto")) for r in pm["seccion_0_bloque"])
    pk.abre_seccion(
        "0E", "### §0.E — `product_model` sucio: **%s** (%d)"
        % (" + ".join("%d %s" % (v, k) for k, v in ver_pm.most_common()), n_pm_b))
    mpm = dic(pm.get("metodo"))
    pk.w("Docs cuyo `product_model` es basura extraída (una fecha, un código). **Ojo: no todos")
    pk.w("son RETAG** — %s. Un `MANTENER` significa que el valor actual"
         % ", ".join("%d %s" % (v, k) for k, v in ver_pm.most_common()))
    pk.w("es correcto y **no hay nada que aplicar**; entra en el bloque para que conste juzgado.")
    pk.w()
    pk.w("Gates de bloque: %s" % ", ".join(
        "`%s`" % g for g in (mpm.get("gates_de_bloque") or [])) or AUSENTE)
    pk.w("K=%s pasadas del juez `%s`, unanimidad exigida."
         % (mpm.get("k_pasadas", AUSENTE), mpm.get("juez", AUSENTE)))
    pk.w()
    for r in pm["seccion_0_bloque"]:
        prop = dic(r.get("propuesta_de_aplicacion"))
        extra = [
            "veredicto **%s** → product_model %s · confianza %s · cita %s" % (
                r.get("veredicto"), ", ".join("`%s`" % m for m in r.get("product_model_propuesto") or []),
                r.get("confianza"), "✓" if r.get("cita_verificada_full_text") else "✗"),
            "cita: %s" % cita(r.get("cita"), 150),
            "razón: %s" % corta(r.get("razon"), 200),
            "aplicar: documents.pm %s · chunks_v2.pm %s · doc_map: %s" % (
                corta(prop.get("documents.product_model"), 40),
                corta(prop.get("chunks_v2.product_model"), 45),
                corta(prop.get("doc_map"), 90)),
        ]
        if r.get("residuo"):
            extra.append("⚑ residuo que NO cierra este sí: %s" % corta(r.get("residuo"), 190))
        pk.fila("`%s` · pm actual «%s» · %s · %s" % (
            r.get("source_file", AUSENTE), r.get("pm_actual", AUSENTE),
            r.get("manufacturer_actual", AUSENTE), plural(r.get("n_chunks"), "chunk")), extra)
    pk.w()

    # ---------------------- §1 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 1 — Una a una (%d)" % individual)
    pk.w()
    pk.w("El residuo real: nada de aquí pasó el gate. Cada fila trae **toda** la evidencia")
    pk.w("junta para decidir sin abrir nada más.")
    pk.w()

    # §1.A — tier B residuo
    pk.abre_seccion("1A", "### §1.A — `doc_map` tier B, residuo (%d)" % n_tb_i)
    pk.w("Motivos de caída (del recibo, uno por línea):")
    pk.w()
    for m, n in sorted(dic(tb.get("motivos_de_individual")).items(), key=lambda kv: -kv[1]):
        pk.w("  - (%s×) %s" % (n, corta(m, 190)))
    pk.w()
    for r in sorted(tb["seccion_1_individual"], key=lambda x: str(x.get("source_file", ""))):
        llm, k2 = dic(r.get("llm")), dic(r.get("k2"))
        extra = [
            "pm doc «%s» · pm chunks «%s» · tokens sin id: %s" % (
                corta(r.get("pm_doc"), 55), corta(r.get("pm_chunks"), 55),
                ", ".join("`%s`" % t for t in r.get("tokens_sin_id") or []) or "—"),
            "ids del packet 12-ago %s → resueltos HOY %s%s" % (
                ids_fmt(r.get("ids_packet_12ago")), ids_fmt(r.get("ids_resueltos_hoy")),
                " · **deriva**" if r.get("deriva_de_ids_desde_el_packet") else ""),
            "juez: **%s** %s · confianza %s · cita %s %s" % (
                llm.get("veredicto", AUSENTE), ids_fmt(r.get("ids_propuestos")),
                llm.get("confianza", AUSENTE),
                "✓" if r.get("cita_verificada_full_text") else "✗", cita(llm.get("cita"), 90)),
            "sujeto según el juez: %s" % corta(llm.get("sujeto"), 150),
        ]
        if k2:
            extra.append("K=2 (2ª pasada): **%s** %s · confianza %s" % (
                k2.get("veredicto"), ids_fmt(k2.get("ids")), k2.get("confianza")))
        extra.append("menciones máximas del sujeto en el documento: %s"
                     % r.get("menciones_maximas_en_el_documento", AUSENTE))
        extra.append("**por qué NO entra en bloque**: %s"
                     % corta("; ".join(r.get("fallos_de_gate") or []) or AUSENTE, 220))
        if r.get("ids_no_consumibles"):
            extra.append("ids NO consumibles (candidate/retirado): %s" % ids_fmt(r["ids_no_consumibles"]))
        if r.get("ids_fuera_de_menu"):
            extra.append("ids fuera del menú cerrado: %s" % ids_fmt(r["ids_fuera_de_menu"]))
        pk.fila("`%s` (%s · %s · %s)" % (
            r.get("source_file", AUSENTE), r.get("manufacturer", AUSENTE),
            plural(r.get("n_chunks"), "chunk"), r.get("estado_refresco", AUSENTE)), extra)
    pk.w()

    # §1.B — candidates residuo (agrupado por motivo dominante)
    pk.abre_seccion("1B", "### §1.B — Candidates, residuo (%d)" % n_ca_i)
    pk.w("Agrupados por **su primer motivo de caída** (el recibo trae la lista completa por")
    pk.w("fila). Un mismo id puede aparecer con varias grafías: eso es exactamente lo que")
    pk.w("hay que adjudicar.")
    pk.w()
    grupos: dict[str, list[dict]] = defaultdict(list)
    for r in ca["seccion_1_individual"]:
        motivos = r.get("motivos_individual") or ["(sin motivo declarado en el recibo)"]
        grupos[motivos[0]].append(r)
    for motivo, filas in sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pk.w("**%s** — %d" % (motivo, len(filas)))
        pk.w()
        for r in sorted(filas, key=lambda x: str(x.get("id", ""))):
            llm, sn = dic(r.get("llm")), dic(r.get("senales"))
            md = dic(sn.get("menciones_doc"))
            mg = dic(sn.get("menciones_muestra_global"))
            otros = [m for m in (r.get("motivos_individual") or [])[1:]]
            extra = ["**%s** · rol %s · confianza %s · cita %s %s" % (
                llm.get("veredicto", AUSENTE), llm.get("rol_en_texto", AUSENTE),
                llm.get("confianza", AUSENTE),
                "✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 85)),
                "doc `%s` · estrictas doc %s / global %s en %s%s" % (
                    corta(dic(r.get("documento")).get("source_pdf_filename"), 46),
                    md.get("estrictas", "?"), mg.get("estrictas", "?"),
                    plural(mg.get("documentos", "?"), "doc"),
                    (" · otros motivos: " + "; ".join(otros)) if otros else "")]
            if llm.get("termino_real"):
                extra.append("el juez propone otra grafía: `%s`" % corta(llm["termino_real"], 60))
            if llm.get("producto_padre"):
                extra.append("producto padre propuesto: `%s`" % corta(llm["producto_padre"], 60))
            pk.fila("`%s` (%s)" % (r.get("id", AUSENTE), r.get("canonical_model", AUSENTE)), extra)
        pk.w()

    # §1.C — pm sucio residuo
    pk.abre_seccion("1C", "### §1.C — `product_model` sucio, residuo (%d)" % n_pm_i)
    for r in pm["seccion_1_individual"]:
        ev = dic(r.get("evidencia"))
        pk.fila("`%s` · pm actual «%s» · %s · %s" % (
            r.get("source_file", AUSENTE), r.get("pm_actual", AUSENTE),
            r.get("manufacturer_actual", AUSENTE), plural(r.get("n_chunks"), "chunk")),
            ["veredicto **%s** · confianza %s · cita %s %s" % (
                r.get("veredicto"), r.get("confianza"),
                "✓" if r.get("cita_verificada_full_text") else "✗", cita(r.get("cita"), 120)),
             "razón: %s" % corta(r.get("razon"), 230),
             "muestra: %s · candidatos impresos: %s" % (
                 corta(ev.get("modo_muestra"), 55),
                 len(ev.get("candidatos_impresos") or []) or "ninguno"),
             "**la pregunta que hay que responder**: %s" % corta(r.get("residuo"), 240),
             "propuesta si no se decide: %s" % corta(
                 dic(r.get("propuesta_de_aplicacion")).get("aviso"), 150)])
    pk.w()

    # ---------------------- §2 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.abre_seccion("2", "## SECCIÓN 2 — Ya no aplican (%d) — **no decides nada**" % n_tb_fuera)
    pk.w("Filas del packet v1 que el refresco contra el estado de HOY dejó sin objeto.")
    pk.w("Se listan para que conste que NO se han perdido, no para adjudicar.")
    pk.w()
    por_motivo: dict[str, list[dict]] = defaultdict(list)
    for r in tb["seccion_2_fuera_del_packet"]:
        por_motivo[str(r.get("estado_refresco", "?"))].append(r)
    for est, filas in sorted(por_motivo.items()):
        pk.w("**%s (%d)** — %s" % (est, len(filas), corta(filas[0].get("motivo_refresco"), 190)))
        pk.w()
        for r in sorted(filas, key=lambda x: str(x.get("source_file", ""))):
            pk.fila("`%s` (%s · %s)" % (
                r.get("source_file", AUSENTE), r.get("manufacturer", AUSENTE),
                plural(r.get("n_chunks"), "chunk")), casilla=False)
        pk.w()

    cierre(pk, ["colisiones", "tierb", "candidates", "pm_sucio"],
           {"SECCIÓN 0": bloque, "SECCIÓN 1": individual, "SECCIÓN 2": n_tb_fuera},
           {"SECCIÓN 0": ["0A", "0B", "0C", "0D", "0E"],
            "SECCIÓN 1": ["1A", "1B", "1C"], "SECCIÓN 2": ["2"]}, total)
    return pk


# ===========================================================================
# 6. PACKET E1b
# ===========================================================================
def construye_e1b(d: dict[str, dict], avisos: list[str]) -> Packet:
    cf = d["confirmar"]
    rv = d["revisar"]

    cf_b = cf["detalle"]["bloque"]
    cf_i = cf["detalle"]["individual"]
    rv_bc = rv["secciones"]["0_bloque_confirmar"]
    rv_br = rv["secciones"]["0_bloque_retirar"]
    rv_i = rv["secciones"]["1_individual"]

    total = len(cf_b) + len(cf_i) + len(rv_bc) + len(rv_br) + len(rv_i)
    bloque = len(cf_b) + len(rv_bc) + len(rv_br)
    individual = len(cf_i) + len(rv_i)

    det = [r for r in cf_b if r.get("ruta") == "determinista"]
    llmr = [r for r in cf_b if r.get("ruta") != "determinista"]

    pk = Packet("e1b", "E1b")
    pk.w("# s320 E1b — Packet de ADJUDICACIÓN **v2 (encogido)** · %s" % UTC)
    pk.w()
    pk.w("**SUPERSEDE a `%s`.**" % V1["e1b"])
    pk.w("Los dos lotes del E1b (**%d** «confirmar» + **%d** «revisar» = **%d casillas**) venían"
         % (len(cf_b) + len(cf_i), len(rv_bc) + len(rv_br) + len(rv_i), total))
    pk.w("de una atestación `ilike` **sin fronteras de palabra**: contaba «CAD-250» dentro de")
    pk.w("«CAD-250-BLED» y «adaptador» dentro de «adaptadores». Dos pasadas hermanas han")
    pk.w("re-medido cada término con **token exacto** y han juzgado sólo lo que la medida no")
    pk.w("zanja.")
    pk.w()
    pk.w("> ### De **%d casillas** → **%d decisiones**" % (total, individual + 1))
    pk.w("> - **1 sí en bloque** cubre **%d filas** (§0, en 4 sub-bloques)." % bloque)
    pk.w("> - **%d una a una** (§1)." % individual)
    pk.w()
    cabecera_comun(pk, avisos)

    # ---------------------- §0 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (%d)" % bloque)
    pk.w()
    pk.w("Puerta del bloque «confirmar» (las 5 condiciones, todas):")
    for c in cf.get("puerta_del_bloque", []):
        pk.w("  %d. %s" % (cf["puerta_del_bloque"].index(c) + 1, c))
    pk.w()
    pk.w("Puerta del bloque «revisar»: %s" % corta(rv.get("criterio_bloque"), 320))
    pk.w()

    # Avisos: no bloquean, pero un «sí» informado los necesita.
    av = dic(cf.get("avisos_bloque"))
    pk.w("> **Avisos del bloque** (%s):" % corta(av.get("que_son"), 120))
    col_nom = av.get("colisiones_de_nombre") or []
    # Se listan ENTERAS, una por línea: es el aviso con más consecuencia del
    # packet (confirmar ambos ids duplica un producto) y recortarlo a 600 chars
    # escondía la mitad justo donde hay que mirar.
    pk.w("> - **colisiones de nombre: %d** — confirmar los dos ids crea DOS productos para un" % len(col_nom))
    pk.w(">   mismo nombre (posible duplicado o alias, no alta separada):")
    for c in col_nom:
        pk.w(">     - `%s` → %s" % (c.get("nombre_normalizado", AUSENTE),
                                    " / ".join("`%s`" % i for i in (c.get("ids") or [])) or AUSENTE))
    ev_min = av.get("evidencia_minima") or []
    pk.w("> - **evidencia mínima (1 solo chunk con token exacto): %d** — %s" % (
        len(ev_min), ", ".join("`%s`" % e.get("id") for e in ev_min) or "—"))
    pk.w("> - **fabricante del manual distinto al del id: %s** filas. No es un fallo (OEM/reventa"
         % av.get("fabricante_del_manual_distinto_al_id", AUSENTE))
    pk.w(">   es la norma en PCI), pero si te importa la marca de origen, mira el recibo.")
    pk.w()
    dv = dic(cf.get("deriva_conteo"))
    pk.w("Deriva de conteo desde el 12-ago (subió/bajó/igual/cayó bajo umbral): %s"
         % ", ".join("%s=%s" % (k, v) for k, v in dv.items()) or AUSENTE)
    rc = dic(rv.get("recuento"))
    pk.w("Del lote «revisar»: filas medidas hoy **%s**, con conteo cambiado desde el 12-ago **%s**,"
         % (rc.get("filas_medidas_hoy", AUSENTE), rc.get("filas_cuyo_conteo_cambio_desde_12ago", AUSENTE)))
    pk.w("mencionadas **sólo por subcadena** (o sea, no atestadas) **%s**."
         % rc.get("filas_con_mencion_solo_por_subcadena", AUSENTE))
    pk.w()

    # §0.A — determinista, en lotes por marca
    pk.abre_seccion("0A", "### §0.A — «confirmar» por **medida determinista, sin juez** (%d)" % len(det))
    pk.w("Aquí no opinó ningún modelo: el término aparece como **token completo** en ≥2 chunks")
    pk.w("y en varios documentos. La medida ES el veredicto. Formato: `MODELO(chunks·docs)`.")
    pk.w("Se agrupan por marca en lotes para que quepan; **cada término está listado** (Ctrl-F)")
    pk.w("y el detalle fila a fila —chunk_id, página, sección, fragmento verbatim— está en el recibo.")
    pk.w()
    por_marca: dict[str, list[dict]] = defaultdict(list)
    for r in det:
        por_marca[marca_de(r.get("id", ""))].append(r)
    for mk, filas in sorted(por_marca.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        items = ["`%s`(%s·%s)" % (r.get("modelo"), r.get("n_chunks_token_exacto"),
                                  r.get("docs_distintos_con_exacta"))
                 for r in sorted(filas, key=lambda x: str(x.get("modelo", "")))]
        pk.lote("**%s** — %s determinista%s" % (mk, plural(len(filas), "confirmación", "confirmaciones"),
                                                "" if len(filas) == 1 else "s"), items, len(filas))
    pk.w()

    # §0.B — vía juez
    pk.abre_seccion("0B", "### §0.B — «confirmar» por **juez, alta + cita verificada** (%d)" % len(llmr))
    pk.w("Formas sospechosas (cortas, sin dígitos, multipalabra) que la medida sola no zanja.")
    pk.w("Banderas léxicas del lote completo: %s"
         % ", ".join("%s=%s" % (k, v) for k, v in dic(cf.get("banderas_lexicas")).items()))
    pk.w()
    for r in sorted(llmr, key=lambda x: str(x.get("id", ""))):
        pk.fila("`%s` (%s) · %s token exacto en %s%s" % (
            r.get("id", AUSENTE), r.get("modelo", AUSENTE),
            plural(r.get("n_chunks_token_exacto", "?"), "chunk"),
            plural(r.get("docs_distintos_con_exacta", "?"), "doc"),
            (" · banderas: " + ",".join(r.get("banderas") or [])) if r.get("banderas") else ""),
            ["cita %s %s" % ("✓" if r.get("cita_verificada") else "✗", cita(r.get("cita"), 100)),
             "por qué: %s" % corta(r.get("por_que"), 160)])
    pk.w()

    # §0.C — revisar → CONFIRMAR
    pk.abre_seccion("0C", "### §0.C — «revisar» → **CONFIRMAR** (%d)" % len(rv_bc))
    pk.w("Candidates ya presentes en el catálogo, atestados **con frontera de palabra** en el")
    pk.w("contenido de `chunks_v2` + cita verificada a texto completo + sin colisión de catálogo.")
    pk.w("Clases del lote completo: %s"
         % ", ".join("%s=%s" % (k, v) for k, v in dic(rv.get("por_clase")).items()))
    pk.w()
    for r in sorted(rv_bc, key=lambda x: str(x.get("id", ""))):
        llm = dic(r.get("llm"))
        pk.fila("`%s` (%s · %s) · frontera hoy %s · prov `%s`" % (
            r.get("id", AUSENTE), r.get("modelo", AUSENTE), r.get("marca", AUSENTE),
            r.get("n_frontera_hoy", "?"), corta(r.get("provenance_doc"), 44)),
            ["cita %s %s" % ("✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 105))])
    pk.w()

    # §0.D — revisar → RETIRAR
    pk.abre_seccion("0D", "### §0.D — «revisar» → **RETIRAR** (%d)" % len(rv_br))
    pk.w("Evidencia POSITIVA de que el término no es un modelo comercial. Van en lista aparte")
    pk.w("porque retirar es destructivo: un «sí» al §0.C no arrastra al §0.D si no quieres.")
    pk.w()
    for r in sorted(rv_br, key=lambda x: str(x.get("id", ""))):
        llm = dic(r.get("llm"))
        pk.fila("`%s` (%s · %s) · frontera hoy %s · prov `%s`" % (
            r.get("id", AUSENTE), r.get("modelo", AUSENTE), r.get("marca", AUSENTE),
            r.get("n_frontera_hoy", "?"), corta(r.get("provenance_doc"), 44)),
            ["cita %s %s" % ("✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 120)),
             "razón: %s" % corta(llm.get("razon"), 200)])
    pk.w()

    # ---------------------- §1 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 1 — Una a una (%d)" % individual)
    pk.w()

    pk.abre_seccion("1A", "### §1.A — «confirmar», residuo (%d)" % len(cf_i))
    pk.w("Desglose: %s" % ", ".join("%s=%s" % (k, v) for k, v in dic(cf.get("desglose_individual")).items()))
    pk.w()
    por_ver: dict[str, list[dict]] = defaultdict(list)
    for r in cf_i:
        por_ver[str(r.get("veredicto", "?"))].append(r)
    for ver, filas in sorted(por_ver.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pk.w("**propuesta del juez: %s (%d)**" % (ver, len(filas)))
        pk.w()
        for r in sorted(filas, key=lambda x: str(x.get("id", ""))):
            ev = dic(r.get("evidencia"))
            par = r.get("parasitos_top") or []
            extra = [
                "medida: `ilike` %s → token exacto **%s** en %s · sólo-parásito %s%s" % (
                    r.get("n_ilike_hoy", "?"), r.get("n_chunks_token_exacto", "?"),
                    plural(r.get("docs_distintos_con_exacta", "?"), "doc"),
                    r.get("n_chunks_solo_parasito", "?"),
                    (" · parásitos: " + ", ".join("%s×%s" % (p.get("token"), p.get("n")) for p in par))
                    if par else ""),
                "banderas: %s · fabricante: %s · %s" % (
                    ", ".join(r.get("banderas") or []) or "ninguna",
                    r.get("coherencia_fabricante", AUSENTE),
                    "; ".join(r.get("motivos_no_determinista") or []) or "—"),
                "juez: **%s** · confianza %s · cita %s %s" % (
                    r.get("veredicto", AUSENTE), r.get("confianza", AUSENTE),
                    "✓" if r.get("cita_verificada") else "✗", cita(r.get("cita"), 95)),
                "por qué: %s" % corta(r.get("por_que"), 175),
            ]
            if ev.get("fragmento"):
                extra.append("evidencia (pág %s · %s): %s" % (
                    ev.get("pagina"), corta(ev.get("seccion"), 32), cita(ev.get("fragmento"), 130)))
            pk.fila("`%s` (%s)" % (r.get("id", AUSENTE), r.get("modelo", AUSENTE)), extra)
        pk.w()

    pk.abre_seccion("1B", "### §1.B — «revisar», residuo (%d)" % len(rv_i))
    pk.w("Agrupados por el motivo que los dejó fuera del bloque.")
    pk.w()
    por_mot: dict[str, list[dict]] = defaultdict(list)
    for r in rv_i:
        por_mot[str(r.get("motivo_seccion", "?"))].append(r)
    for mot, filas in sorted(por_mot.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        pk.w("**%s — %d**" % (mot, len(filas)))
        pk.w()
        for r in sorted(filas, key=lambda x: str(x.get("id", ""))):
            llm = dic(r.get("llm"))
            extra = ["**%s** · confianza %s · cita %s %s" % (
                llm.get("veredicto", AUSENTE), llm.get("confianza", AUSENTE),
                "✓" if r.get("cita_verificada") else "✗", cita(llm.get("cita"), 95)),
                "frontera hoy %s · substring %s · chunks con ese product_model %s · prov `%s`%s" % (
                    r.get("n_frontera_hoy", "?"), r.get("n_substring_hoy", "?"),
                    r.get("n_chunks_con_ese_product_model", "?"),
                    corta(r.get("provenance_doc"), 40),
                    (" · **colisión**: " + ids_fmt(r.get("colision_catalogo")))
                    if r.get("colision_catalogo") else "")]
            pk.fila("`%s` (%s · %s)" % (
                r.get("id", AUSENTE), r.get("modelo", AUSENTE), r.get("marca", AUSENTE)), extra)
        pk.w()

    cierre(pk, ["confirmar", "revisar"],
           {"SECCIÓN 0": bloque, "SECCIÓN 1": individual},
           {"SECCIÓN 0": ["0A", "0B", "0C", "0D"], "SECCIÓN 1": ["1A", "1B"]}, total)
    return pk


# ===========================================================================
# 7. PACKET E2
# ===========================================================================
def construye_e2(d: dict[str, dict], avisos: list[str]) -> Packet:
    al = d["altas"]
    blo = al["seccion_0_bloque"]
    ind = al["seccion_1_individual"]
    obs = al.get("obsoletas", [])
    res = dic(al.get("resumen"))
    total = res.get("total_packet", len(blo) + len(ind) + len(obs))

    con_chunks = sorted([r for r in blo if (r.get("chunk_count_hoy") or 0) > 0],
                        key=lambda r: (-(r.get("chunk_count_hoy") or 0), str(r.get("model"))))
    sin_chunks = sorted([r for r in blo if not (r.get("chunk_count_hoy") or 0)],
                        key=lambda r: str(r.get("model", "")))

    pk = Packet("e2", "E2")
    pk.w("# s320 E2 — Packet de ADJUDICACIÓN **v2 (encogido)** · %s" % UTC)
    pk.w()
    pk.w("**SUPERSEDE a `%s`.**" % V1["e2"])
    pk.w("Aquel packet listaba **%d altas** del detector en 25 lotes de 50, todas con el mismo" % total)
    pk.w("peso. Una pasada hermana las ha refrescado contra el estado de HOY (catálogo `%s`,"
         % (dic(al.get("estado_de_hoy")).get("catalogo_commit", AUSENTE)))
    pk.w("%s términos resolubles, %s docs activos, %s chunks leídos) y las ha separado por RIESGO"
         % (dic(al.get("estado_de_hoy")).get("terminos_resolubles_hoy", "?"),
            dic(al.get("estado_de_hoy")).get("docs_activos", "?"),
            dic(al.get("estado_de_hoy")).get("chunks_leidos", "?")))
    pk.w("de contaminación del detector, no por orden alfabético.")
    pk.w()
    pk.w("> ### De **%d casillas** → **%d decisiones**" % (total, 1 + len({tuple(r.get('reglas') or ['-'])[0] for r in ind})))
    pk.w("> - **1 sí en bloque** cubre **%d altas SEGURAS** (§0)." % len(blo))
    pk.w("> - El residuo (**%d**) va en **%d lotes por regla de riesgo** (§1): puedes asentir por"
         % (len(ind), len({tuple(r.get('reglas') or ['-'])[0] for r in ind})))
    pk.w(">   lote, o bajar fila a fila al recibo — cada término está listado aquí.")
    pk.w("> - **%d obsoletas** (§2) se cayeron solas. No decides nada." % len(obs))
    pk.w()
    cabecera_comun(pk, avisos)

    pk.w("**Por qué el riesgo importa aquí y no en los otros packets** — %s"
         % corta(dic(al.get("reglas")).get("por_que"), 300))
    pk.w()
    pk.w("**Qué compra realmente este sí** (del recibo, sin adornar): %s"
         % corta(al.get("nota_whisper"), 420))
    pk.w()

    # ---------------------- §0 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 0 — Aplicables EN BLOQUE si asientes (%d)" % len(blo))
    pk.w()
    pk.w("Regla SEGURO: %s" % corta(dic(al.get("reglas")).get("SEGURO (bloque)"), 400))
    pk.w()
    pk.w("Vías de resolución en el catálogo gobernado: %s"
         % ", ".join("%s=%d" % (k, v) for k, v in Counter(r.get("via_hoy") for r in blo).most_common()))
    pk.w()

    pk.abre_seccion("0A", "### §0.A — Con presencia en el corpus HOY (%d) — las que más pesan" % len(con_chunks))
    pk.w("Estas sí mueven el `all_models()` ordenado por `chunk_count` y pueden llegar al hint")
    pk.w("de Whisper. Una línea por alta.")
    pk.w()
    for r in con_chunks:
        pk.fila("`%s` · vía %s · **%s** (packet decía %s) · ids %s%s" % (
            r.get("model", AUSENTE), r.get("via_hoy", AUSENTE),
            plural(r.get("chunk_count_hoy", "?"), "chunk"), r.get("chunk_count_packet", "?"),
            ids_fmt(r.get("ids"), 4),
            (" · alias-base que genera: " + ", ".join("`%s`" % b for b in r["base_alias_generada"]))
            if r.get("base_alias_generada") else ""))
    pk.w()

    pk.abre_seccion("0B", "### §0.B — Sin chunks hoy (%d) — mejoran la query escrita, no el dictado" % len(sin_chunks))
    pk.w("`chunk_count_hoy = 0` en las %d: no llegan al hint de Whisper (capado a ~1000 chars)," % len(sin_chunks))
    pk.w("pero sí al `imatch` posterior sobre texto escrito. Riesgo de contaminación: **ninguna**")
    pk.w("cumple la regla SEGURO por accidente — todas mezclan letras+dígitos, ≥5 chars útiles y")
    pk.w("no generan alias-base ancho. En lotes por vía; **cada término listado** (Ctrl-F).")
    pk.w()
    por_via: dict[str, list[dict]] = defaultdict(list)
    for r in sin_chunks:
        por_via[str(r.get("via_hoy", "?"))].append(r)
    for via, filas in sorted(por_via.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        # Se trocea en lotes de 60 para que ninguna casilla tape demasiadas filas
        # de golpe: un «sí» a 300 términos invisibles no es un sí informado.
        for i in range(0, len(filas), 60):
            trozo = filas[i:i + 60]
            pk.lote("vía **%s** — lote %d/%d (%s)" % (
                via, i // 60 + 1, (len(filas) + 59) // 60, plural(len(trozo), "alta")),
                ["`%s`" % r.get("model") for r in trozo], len(trozo))
    pk.w()

    # ---------------------- §1 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.w("## SECCIÓN 1 — Una a una (%d), agrupadas en lotes por regla de riesgo" % len(ind))
    pk.w()
    pk.w("Clases: %s" % ", ".join("%s=%s" % (k, v) for k, v in dic(res.get("individual_por_clase")).items()))
    pk.w()
    pk.w("**Los 20 más peligrosos** (medidos: menciones reales en el contenido × documentos")
    pk.w("distintos). Si uno de éstos entra mal, contamina TODAS las consultas — es la clase")
    pk.w("del caso FUEGO. Van con casilla propia:")
    pk.w()
    pk.abre_seccion("1TOP", "### §1.0 — Top peligrosos (%d) — decisión individual"
                    % len(al.get("top_peligrosos") or []))
    modelos_ind = {r.get("model"): r for r in ind}
    for t in al.get("top_peligrosos") or []:
        r = modelos_ind.get(t.get("model")) or {}
        pk.fila("`%s` · reglas: %s · **%s menciones** en %s · vía %s · ids %s" % (
            t.get("model", AUSENTE), ", ".join(t.get("reglas") or []),
            t.get("menciones_en_contenido", "?"), plural(t.get("docs_distintos_muestra", "?"), "doc"),
            r.get("via_hoy", "?"), ids_fmt(r.get("ids"), 3)),
            ["alias-base que generaría: %s" % (
                ", ".join("`%s`" % b for b in r.get("base_alias_generada") or []) or "ninguno")])
    pk.w()
    pk.w("> Los 20 de arriba **también** aparecen en su lote de regla abajo (para que cada lote")
    pk.w("> esté completo). No los cuentes dos veces: el total de la §1 es %d." % len(ind))
    pk.w()

    pk.abre_seccion("1", "### §1.1 — Lotes por regla (%d altas)" % len(ind))
    pk.w("Cada alta se asigna a **su primera regla** (el recibo trae todas las reglas de cada")
    pk.w("fila). Formato: `MODELO` o `MODELO(chunks)` si tiene presencia en corpus.")
    pk.w()
    # Partición exacta por primera regla: garantiza que la suma de lotes = 669.
    por_regla: dict[str, list[dict]] = defaultdict(list)
    detalle_regla: dict[str, str] = {}
    for r in ind:
        reglas = r.get("reglas") or ["(sin regla declarada en el recibo)"]
        clave = reglas[0]
        por_regla[clave].append(r)
        for m in r.get("motivos") or []:
            if m.get("regla") == clave and clave not in detalle_regla:
                detalle_regla[clave] = str(m.get("detalle", ""))
    for regla, filas in sorted(por_regla.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        rec = Counter(str(r.get("recomendacion", "")) for r in filas).most_common(1)[0][0]
        items = []
        for r in sorted(filas, key=lambda x: str(x.get("model", ""))):
            cc = r.get("chunk_count_hoy") or 0
            items.append("`%s`%s" % (r.get("model"), ("(%d)" % cc) if cc else ""))
        pie = ["qué significa: %s" % corta(detalle_regla.get(regla) or AUSENTE, 190),
               "recomendación del recibo: **%s**" % corta(rec, 120)]
        pk.lote("regla **%s** — %s" % (regla, plural(len(filas), "alta")), items, len(filas), pie)
        pk.w()

    # ---------------------- §2 -------------------------------------------
    pk.w("---")
    pk.w()
    pk.abre_seccion("2", "## SECCIÓN 2 — Obsoletas (%d) — **no decides nada**" % len(obs))
    pk.w("Estaban en el packet v1 y ya no aplican tras el refresco. Motivos: %s"
         % ", ".join("%s=%s" % (k, v) for k, v in dic(res.get("obsoletas_por_motivo")).items()))
    pk.w()
    for r in obs:
        pk.fila("`%s` (vía packet %s) — %s · %s" % (
            r.get("model", AUSENTE), r.get("via_packet", AUSENTE),
            r.get("motivo", AUSENTE), corta(r.get("detalle"), 150)), casilla=False)
    pk.w()

    notas = al.get("refresco_notas") or []
    if notas or al.get("sub_bloque_relajable_solo_letras"):
        # Apéndice con encabezado PROPIO: colgado bajo «SECCIÓN 2 — Obsoletas»
        # se leía como si estas filas también fueran obsoletas, que es lo
        # contrario de lo que son.
        pk.w("---")
        pk.w()
        pk.w("## Apéndice — contexto, no decisiones")
        pk.w()
    if notas:
        pk.w("**Notas de refresco** (%d cambios de `chunk_count` entre el packet y hoy; no son" % len(notas))
        pk.w("decisiones, explican por qué una cifra no cuadra con la v1):")
        pk.w()
        for n in notas[:12]:
            pk.w("- `%s` · %s: packet %s → hoy %s" % (
                n.get("model"), n.get("campo"), n.get("packet"), n.get("hoy")))
        if len(notas) > 12:
            pk.w("- …y %d más en el recibo." % (len(notas) - 12))
        pk.w()

    sub = al.get("sub_bloque_relajable_solo_letras") or []
    if sub:
        pk.w("**Sub-bloque relajable, si quieres apurar** (%d): altas de la §1 marcadas sólo por" % len(sub))
        pk.w("`solo-letras-sin-digitos` que el recibo señala como relajables a bloque. **No están**")
        pk.w("**incluidas en el sí de la §0** — es una decisión aparte y consciente:")
        pk.w()
        for ln in envuelve(["`%s`" % s for s in sub], 108, ""):
            pk.w(ln)
        pk.w()

    cierre(pk, ["altas"],
           {"SECCIÓN 0": len(blo), "SECCIÓN 1": len(ind), "SECCIÓN 2": len(obs)},
           {"SECCIÓN 0": ["0A", "0B"], "SECCIÓN 1": ["1"], "SECCIÓN 2": ["2"]}, total)
    # El §1.0 (top peligrosos) es un REALCE de filas que ya cuentan en §1.1: se
    # excluye del invariante a propósito y se declara arriba en el propio packet.
    return pk


# ---------------------------------------------------------------------------
# 8. CIERRE COMÚN + AUTO-VERIFICACIÓN
# ---------------------------------------------------------------------------
def cierre(pk: Packet, claves_recibo: list[str], esperado: dict[str, int],
           mapa: dict[str, list[str]], total: int) -> None:
    pk.w("---")
    pk.w()
    pk.w("## Recibos (la traza completa, fila a fila)")
    pk.w()
    for k in claves_recibo:
        meta = RECIBOS[k]
        pk.w("- `%s` — %d filas (%d bloque / %d individual)"
             % (meta["path"].relative_to(ROOT).as_posix(), meta["total"],
                meta["bloque"], meta["individual"]))
    pk.w("- Ensamblado por `scripts/s322_packets_v2.py` (determinista, sin LLM) el %s." % UTC)
    pk.w()
    pk.w("## Auto-verificación del encabezado")
    pk.w()
    pk.w("Filas declaradas arriba vs filas REALMENTE escritas en este fichero:")
    pk.w()
    ok = True
    for nombre, esp in esperado.items():
        real = pk.total_filas(mapa[nombre])
        cas = sum(pk.casillas[k] for k in mapa[nombre])
        marca = "✓" if real == esp else "✗ **DESCUADRE**"
        ok = ok and real == esp
        pk.w("- **%s**: declaradas %d · escritas %d · casillas %d — %s"
             % (nombre, esp, real, cas, marca))
    suma = sum(esperado.values())
    pk.w("- **TOTAL**: %d = %s %s" % (
        suma, " + ".join(str(v) for v in esperado.values()),
        "✓ (cuadra con las %d casillas de la v1)" % total if suma == total
        else "✗ **DESCUADRE con el total v1 (%d)**" % total))
    if not ok or suma != total:
        pk.w()
        pk.w("> ⚠ El invariante NO cuadra. No te fíes de las cifras de la cabecera.")
    pk.w()


# ---------------------------------------------------------------------------
# 9. MAIN
# ---------------------------------------------------------------------------
def main() -> int:
    datos = carga()
    avisos = chequea_drift(datos)
    if avisos:
        print("AVISOS DE DRIFT:")
        for a in avisos:
            print("  -", a)

    packets = {
        "e1": construye_e1(datos, avisos),
        "e1b": construye_e1b(datos, avisos),
        "e2": construye_e2(datos, avisos),
    }

    # --- INVARIANTE DURO: se recalcula fuera del markdown y aborta si falla ---
    invariantes = {
        "e1": ({"SECCIÓN 0": ["0A", "0B", "0C", "0D", "0E"],
                "SECCIÓN 1": ["1A", "1B", "1C"], "SECCIÓN 2": ["2"]}, 253),
        "e1b": ({"SECCIÓN 0": ["0A", "0B", "0C", "0D"], "SECCIÓN 1": ["1A", "1B"]}, 620),
        "e2": ({"SECCIÓN 0": ["0A", "0B"], "SECCIÓN 1": ["1"], "SECCIÓN 2": ["2"]}, 1235),
    }
    fallos = []
    for clave, (mapa, total_v1) in invariantes.items():
        pk = packets[clave]
        suma = sum(pk.total_filas(v) for v in mapa.values())
        if suma != total_v1:
            fallos.append("%s: filas renderizadas %d != casillas v1 %d" % (clave, suma, total_v1))
    if fallos:
        sys.exit("ABORTA sin escribir — el invariante de conteo falla:\n  " + "\n  ".join(fallos))

    resumen = {}
    for clave, pk in packets.items():
        destino = SALIDAS[clave]
        destino.write_text(pk.texto(), encoding="utf-8")
        n_lineas = len(pk.texto().splitlines())
        # Guardarraíl de legibilidad: avisa si alguna sección se pasó de largo.
        largas = {k: pk.lineas_de_seccion(k) for k in pk.filas
                  if pk.lineas_de_seccion(k) > UMBRAL_LINEAS_SECCION}
        resumen[clave] = {
            "fichero": destino.as_posix(),
            "lineas": n_lineas,
            "filas_por_seccion": dict(pk.filas),
            "casillas_por_seccion": dict(pk.casillas),
            "secciones_largas": largas,
        }
        print("ESCRITO %s · %d líneas · filas %s"
              % (destino.name, n_lineas, dict(pk.filas)))
        if largas:
            print("  aviso de legibilidad (>%d líneas): %s" % (UMBRAL_LINEAS_SECCION, largas))

    recibo = {
        "que_es": "Ensamblado determinista (sin LLM) de los tres packets de adjudicación v2 "
                  "a partir de los 7 recibos hermanos de s322f/s322g. PROPUESTA: no se aplicó nada.",
        "utc": UTC,
        "solo_lectura_sobre": [RECIBOS[k]["path"].relative_to(ROOT).as_posix() for k in RECIBOS],
        "no_se_aplico_nada": True,
        "escrituras": [SALIDAS[k].relative_to(ROOT).as_posix() for k in SALIDAS],
        "avisos_de_drift": avisos,
        "packets": resumen,
        "antes_despues": {
            "E1": {"casillas_v1": 253, "bloque": 144, "individual": 97, "ya_no_aplican": 12},
            "E1b": {"casillas_v1": 620, "bloque": 475, "individual": 145},
            "E2": {"casillas_v1": 1235, "bloque": 562, "individual": 669, "obsoletas": 4},
        },
    }
    out = EVALS / "s322_packets_v2_recibo.json"
    out.write_text(json.dumps(recibo, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RECIBO", out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
