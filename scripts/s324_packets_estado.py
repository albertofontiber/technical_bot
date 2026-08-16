# -*- coding: utf-8 -*-
"""s324 — Anota en los packets v2 (los ficheros que Alberto abre) el ESTADO tras el lote aplicado:
qué está aplicado (con recibo), qué queda pendiente de su sí y por qué, y marca fila a fila las
casillas del E1 que ya no requieren decisión. Idempotente (borra y reescribe su propio bloque y sus
propias marcas). No toca las anotaciones de Alberto.
"""
from __future__ import annotations
import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
E1 = ROOT / "evals/s320_e1_packet_adjudicacion_v2.md"
E1B = ROOT / "evals/s320_e1b_packet_adjudicacion_v2.md"
E2 = ROOT / "evals/s320_e2_packet_adjudicacion_v2.md"
INI, FIN = "<!-- s324-estado:inicio -->", "<!-- s324-estado:fin -->"
MARCA = "      ↳ **s324:** "


def bloque(texto: str, cuerpo: str) -> str:
    texto = re.sub(re.escape(INI) + r".*?" + re.escape(FIN) + r"\n?", "", texto, flags=re.S)
    # insertar tras el titular (primera línea)
    partes = texto.split("\n", 1)
    return partes[0] + "\n\n" + INI + "\n" + cuerpo.strip() + "\n" + FIN + "\n" + (partes[1] if len(partes) > 1 else "")


def marcar(texto: str, estados: dict[str, str], clave_rx: str) -> tuple[str, int]:
    """Añade/actualiza una línea de estado bajo cada casilla `- [ ] \\`<clave>\\`` cuya clave esté en `estados`."""
    texto = re.sub(r"\n" + re.escape(MARCA) + r"[^\n]*", "", texto)   # idempotencia
    n = 0
    def rep(m):
        nonlocal n
        k = m.group(2)
        est = estados.get(k) or estados.get(k.lower())
        if not est:
            return m.group(0)
        n += 1
        return m.group(0) + "\n" + MARCA + est
    texto = re.sub(r"(^- \[ \] `)(" + clave_rx + r")(`[^\n]*)", rep, texto, flags=re.M)
    return texto, n


def main() -> None:
    plan = json.loads((ROOT / "evals/s324_lote_firmado_plan_v1.json").read_text(encoding="utf-8"))
    recibo = sorted((ROOT / "evals").glob("s324_lote_firmado_aplicar_*.json"))[-1].name
    utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")

    # ── E1: estados por source_file (doc_map) y por id (candidates) ──
    est_doc: dict[str, str] = {}
    for row in plan["doc_map_altas"]:
        est_doc[row["source_file"].lower()] = f"✅ APLICADO ({', '.join(sorted(set(row['reglas'])))}) → {len(row['entries'])} id(s) · recibo `{recibo}`"
    for m in plan["doc_map_modificaciones"]:
        est_doc[m["source_file"].lower()] = f"✅ APLICADO (modificación {m['regla']}) → {len(m['entries_nuevas'])} id(s)"
    for p in plan.get("pendiente_alberto_R1prima", []):
        est_doc[p["source_file"].lower()] = (f"⏳ PENDIENTE DE TI — R1' (dúo r32: no estaba firmada): ¿atestar solo los {len(p['R1prima_cenida'])} modelos que el doc NOMBRA "
                                             f"o los {len(p['R1_completa'])} de la serie? Contesta «R1' OK» o «R1 completa» y se aplica.")
    for x in plan["no_aplicar"]:
        q = str(x["que"]).lower()
        if q.startswith("996-130"):
            est_doc["996-130-000-3 manuel d'utilisation zx_hlsi"] = "⏳ PENDIENTE DE TI — fragmento FR de 1 chunk (mismo caso que los PT retirados): ¿BAJA? (no se atesta hasta decidirlo)"
        if q.startswith("hlsi-ti-007"):
            est_doc["hlsi-ti-007_vsn-4rel"] = "⏳ re-ingesta OCR primero (tu adjudicación: modelo VSN-4REL); atestación después"
        if q.startswith("ma-dt-1160"):
            est_doc["ma-dt-1160"] = "✅ RETIRADO del corpus (tu adjudicación s323) — recibo `s324_retirar_docs_aplicar_20260816T105639Z.json`"
    for sf in ("mie-mi-120p", "miemu520p", "4188-1132-pt issue 4_04_2025-qref"):
        est_doc[sf] = "✅ RETIRADO del corpus (fragmento PT con hermano ES; tu sí del 16-ago)"
    est_id: dict[str, str] = {}
    for a in plan["products_altas"]:
        est_id[a["row"]["id"]] = f"✅ ALTA aplicada ({a['regla']}) · cita verificada en {a['doc']}"
    for x in plan["no_aplicar"]:
        q = str(x["que"]); mot = x["motivo"]
        if q.startswith(("kidde:", "notifier:", "morley:", "spectrex:", "avotec:", "sensitron:", "aritech:", "xtralis:", "fidegas:")):
            if "R6" in mot:
                est_id[q] = "✅ RESUELTO por R6 (fuente retirada → no se da de alta): no decides nada"
            elif "clase §0.C" in mot or "sí de Alberto" in mot:
                est_id[q] = "⏳ PENDIENTE DE TI — nombre real CON barra (no es concatenación): un «sí» lo da de alta"
            elif "Puerta A" in mot:
                est_id[q] = "⏳ en cuarentena (acrónimo corto): el predicado validado NO lo cubre; no se da de alta sin tu sí"
            elif "K=5" in mot:
                est_id[q] = "⏳ confianza media: pendiente de re-juicio K=5 o de tu sí"
            elif "NO aparece como token" in mot:
                est_id[q] = "✅ RESUELTO por R7 (el componente no tiene cita propia → no se da de alta)"
    # ids concatenados del draft cuyos componentes se aplicaron por R7
    for k in ("kidde:ke-dp3121b-ke-dp3121b-snv", "kidde:ke-dp3121w-ke-dp3121w-sn", "kidde:ke-dp3121w-ke-dp3121w-sn-ke-dp3121w-snv",
              "kidde:ke-dba-adpw-kil-ke-dba-adpw-zit", "kidde:ke-iu3111-zme-kit-2x-ae1-09", "kidde:n-io-mbx-1-n-io-mbx-2",
              "kidde:n-io-sbx-1g-n-io-sbx-2g", "fidegas:s-2-t1-y-s-3-t1"):
        est_id[k] = "✅ RESUELTO por R7: partido en sus componentes con cita propia (ver altas / doc_map aplicados); el id concatenado no se crea"
    est_id["kidde:ke-dba-labw-l1s-ke-dba-labw-l2s-ke-dba-labw-l3s-ke-dba-labw-l4s"] = "✅ RESUELTO por R7: ningún componente L1S..L4S aparece como token → no se da de alta (el juez propone KE-DBA-LABW-S: si quieres ese alta, dilo)"
    est_id["kidde:zlsm-me-zlsm-mr"] = "✅ RESUELTO por R7: ZLSM-ME/ZLSM-MR no aparecen como token en sus docs → no se da de alta"
    est_id["notifier:nx2-r-r-y-nx5-r-r"] = "⏳ PENDIENTE DE TI — NX2/R/R y NX5/R/R: nombre con barra, 1 sola mención en tabla (dúo r32): ¿alta?"
    # §0.C (32 altas en bloque): las que R4/R7 ya crearon quedan cubiertas; el resto siguen en el bloque (tu sí)
    tri = json.loads((ROOT / "evals/s322g_e1_candidatos_triage_v1.json").read_text(encoding="utf-8"))
    aplicadas = {a["row"]["id"] for a in plan["products_altas"]}
    for f in tri["seccion_0a_alta_en_bloque"]:
        if f["id"] in aplicadas:
            est_id[f["id"]] = f"✅ ALTA ya aplicada en s324 (R4/R7, cita verificada) — esta casilla del bloque §0.C queda cubierta"
        else:
            est_id[f["id"]] = "⏳ en el bloque §0.C — tu «sí» (pasará por el gate del detector antes de escribirse)"

    t = E1.read_text(encoding="utf-8")
    t, n_doc = marcar(t, est_doc, r"[^`]+")
    t, n_id = marcar(t, est_id, r"[a-z0-9_-]+:[a-z0-9._+-]+")
    pend_r1 = plan.get("pendiente_alberto_R1prima", [])
    cuerpo = f"""> ## 🟢 ESTADO s324 ({utc}) — lo que ya NO tienes que decidir, y lo que sí
> **Aplicado con recibo `{recibo}`** (dúo r32 Sol+Fable antes de escribir; verificación posterior en censo PASS):
> - **§0.A** (49) ✅ · **§0.B** (38 limpias + 4 «tu ojo» + tus anotaciones) ✅ **APLICADO** — {sum(1 for r in plan['doc_map_altas'] if r['reglas'][0].startswith('§0.B'))} filas doc_map.
> - **§1.A** (13): 10 resueltas por tus REGLAS R1/R2/R4/R5 (`evals/s324_reglas_residuo_adjudicacion_v1.json`) — 3 quedan pendientes de **R1'** (abajo).
> - **§1.B** (84): las de R6 (7) y R7 (23+4) están RESUELTAS con prueba (altas aplicadas o descartadas); acrónimos cortos (17) y confianza media (14) siguen en cuarentena; todo marcado fila a fila.
> - Retirados del corpus: MA-DT-1160 (tu adjudicación) + 6 fragmentos PT con hermano ES.
>
> **PENDIENTE DE TI (lo único que queda en este fichero):**
> 1. **R1'** ({len(pend_r1)} docs: {', '.join(p['source_file'][:34] for p in pend_r1)}): «si el documento NOMBRA modelos de la serie, atestar solo los nombrados» — ¿OK? (Sol r32: es criterio nuevo, no lo firmaste.)
> 2. **§0.C** (32 altas) · **§0.D** (17 retirar) · **§0.E** (3): tus tres «sí» en bloque siguen abiertos — pero OJO: las altas/confirmaciones pasan por el gate del detector (censo del radio de explosión) antes de escribirse, como este lote.
> 3. Nombres reales con barra (DOA FJ/CPD, EFS/EM 8, CONV232/485, PUL-D/EXT, PUL-P/EXT, STS/CKD+, 20/20MI, 20/20R, NX2/R/R, NX5/R/R): un «sí» = alta.
> 4. Paraguas «2X-A» (familia): el gate léxico lo frenó (core «2·x·a» dispara en «2 x a»); lo adjudicado (guía → familia) ya está cubierto vía doc_map. ¿Lo quieres igualmente?
> 5. Baja del fragmento FR `996-130-000-3 manuel d'utilisation ZX` (1 chunk) — ¿sí?
> 6. Abiertos no bloqueantes: VSN2-PLUS / «Plus2» (solo en docs NFS-SUPRA/UCIP); OCR de HLSI-TI-007.
>
> Marcas fila a fila: `↳ s324:` bajo cada casilla (✅ = no decides nada · ⏳ = tuya)."""
    t = bloque(t, cuerpo)
    E1.write_text(t, encoding="utf-8")
    print(f"E1: {n_doc} casillas doc marcadas, {n_id} casillas id marcadas")

    # ── E1b: solo el bloque de estado (los bloques siguen abiertos; aviso del gate) ──
    t = E1B.read_text(encoding="utf-8")
    cuerpo = f"""> ## 🟡 ESTADO s324 ({utc})
> Este packet sigue **ABIERTO**: sus 4 bloques (474 confirmaciones) y las 146 «una a una» esperan tu sí. Dos cosas nuevas:
> - **Tu «sí» ya no aplica en seco**: confirmar un candidate activa sus alias y mete términos en el detector (DEC-220 r30). Cada bloque pasará por el **censo del radio de explosión + gate** que ya funcionó en s324 (`scripts/s324_lote_firmado_writer.py`: +28 términos, 0 gold perdidas, 0 disparos en negativos) ANTES de escribirse. Es trabajo mío, no tuyo.
> - **§1.A «retirar» (19) y §0.D (4)**: el predicado de reconstruibilidad (Puerta A) quedó VALIDADO contra el doble control (`evals/s324_puerta_a_predicado_v1.json`) pero **0/18** de estas filas son de esa clase (son palabras genéricas / part-numbers): siguen en cuarentena hasta tu sí; en cuarentena no hacen daño.
> - Ya aplicado por reglas (no está en este packet): confirmados morley:dx1e/dx2e/dx4e (+3 cajas) y morley:vsn-12-plus (R2); retiradas las etiquetas kidde:2x-at y notifier:vsn-plus (→ paraguas 2X-AT / VSN PLUS)."""
    E1B.write_text(bloque(t, cuerpo), encoding="utf-8")
    print("E1b: bloque de estado")

    # ── E2 ──
    t = E2.read_text(encoding="utf-8")
    cuerpo = f"""> ## 🟡 ESTADO s324 ({utc})
> El bloque de altas seguras y los lotes por riesgo esperan tu sí. El catálogo gobernado cambió en s324 (+13 productos, +7 confirmaciones, +3 paraguas, −2 etiquetas), así que el snapshot candidato se **re-derivó** (`s320_e2_snapshot_derivado.py`) y el split por riesgo se refrescó (`s322f_e2_altas_split_v1.json`): **1.326 altas = 596 en bloque + 730 individuales** (antes 1.235 = 562 + 669; las +91 son en su mayoría lo confirmado/dado de alta hoy). Gates: la variante **conservadora** (equivalencia con el snapshot vivo) **PASS** (0 pérdidas, voz idéntica); la completa sigue con las mismas 6 pérdidas conocidas de golds (VESDA-E-VEP, CCD-103, NFS-Supra, 40/40, MAD-472 — bajas que este packet adjudica). Los conteos del cuerpo de este fichero son del 15-ago; el bloque/lotes se regenerarán al aplicar tu sí."""
    E2.write_text(bloque(t, cuerpo), encoding="utf-8")
    print("E2: bloque de estado")


if __name__ == "__main__":
    main()
