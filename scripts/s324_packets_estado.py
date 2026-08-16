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
        est = estados.get(k) or estados.get(k.lower()) or estados.get(re.sub(r"\.pdf$", "", k.lower()))
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
    r1p = ROOT / "evals/s324b_r1prima_plan_v1.json"
    r1p_aplicado = r1p.exists() and any((ROOT / "evals").glob("s324b_r1prima_aplicar_*.json"))
    for p in plan.get("pendiente_alberto_R1prima", []):
        if r1p_aplicado:
            est_doc[p["source_file"].lower()] = f"✅ APLICADO (R1' — tu «R1' OK» del 16-ago) → {len(p['R1prima_cenida'])} modelos NOMBRADOS de {len(p['R1_completa'])} de la serie · recibo `s324b_r1prima_aplicar_*.json`"
        else:
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
    p0c = ROOT / "evals/s324b_lote_0c_plan_v1.json"
    plan0c = json.loads(p0c.read_text(encoding="utf-8")) if p0c.exists() else None
    ap0c = {a["row"]["id"]: a for a in (plan0c or {}).get("products_altas", [])}
    rec0c = sorted((ROOT / "evals").glob("s324b_lote_0c_aplicar_*.json"))
    rec0c = rec0c[-1].name if rec0c else None
    RENOM = {"spectrex:40-40m": "spectrex:s40-40m", "spectrex:40-40r": "spectrex:s40-40r", "spectrex:40-40u": "spectrex:s40-40u (+ spectrex:s40-40ub)"}
    for f in tri["seccion_0a_alta_en_bloque"]:
        fid = f["id"]
        if fid in aplicadas:
            est_id[fid] = f"✅ ALTA ya aplicada en s324 (R4/R7, cita verificada) — esta casilla del bloque §0.C queda cubierta"
        elif rec0c and (fid in ap0c or RENOM.get(fid, "").split(" ")[0] in ap0c):
            tid = fid if fid in ap0c else RENOM[fid].split(" ")[0]
            extra = " (+ S40/40UB)" if fid == "spectrex:40-40u" else ""
            est_id[fid] = f"✅ ALTA aplicada (lote §0.C, tu revisión del 16-ago) como `{tid}`{extra} · cita verificada en {ap0c[tid]['doc'][:40]} · recibo `{rec0c}`"
        elif rec0c and fid == "aritech:2x-a":
            est_id[fid] = "⏳ PENDIENTE DE TI — paraguas «2X-A» (familia): el revisor señaló que tu nota adjudica el ALCANCE, no el riesgo léxico del gate («2 x a» con espacios lo dispararía; 0 casos en 96 consultas reales) ni si incluye la sub-serie táctil 2X-AT (11 de 38). ¿Lo quieres igualmente, con 2X-AT dentro?"
        elif rec0c and fid == "morley:dxc-connexion":
            est_id[fid] = "✅ RESUELTO (tu nota): la FAQ atesta a la familia DXc (dxc1/dxc2/dxc4) en el doc_map; no se crea producto"
        elif rec0c and fid == "morley:vision-supra":
            est_id[fid] = "✅ RESUELTO (tu «baja, confirmo»): documento retirado del corpus; sin alta"
        elif rec0c and fid == "notifier:stratos":
            est_id[fid] = "✅ RESUELTO (tu «este doc es paraguas»): STRATOS = paraguas de familia con sus modelos ya catalogados bajo nombre Notifier (LaserStar-HSSD-2 = Stratos HSSD-2, MINILÁSER25 = Stratos Micra 25, MINILASER 100 = Stratos Micra 100); MADT731_02 → doc_map a los 3; retirados 2 alias erróneos (Stratos-HSSD→SenseNET, Stratos-HSSD detector→MiniLáser25) · recibo `s324b_stratos_aplicar_*.json`"
        elif rec0c and fid == "notifier:nfxi-bsf-wch":
            est_id[fid] = "✅ ALTA aplicada como `notifier:nfxi-bsf-wch` (grafía firmada; 3 docs INSPIRE) + alias `NFXI-BSF-WC` (5 docs AM-8200) — si WC y WCH fueran DOS productos, dilo y se separan"
        else:
            est_id[fid] = "✅ ACEPTADO por Alberto (§0.C revisado 16-ago, notas consolidadas) → entra en el lote §0.C tras el gate del detector"

    # §0.D (17 RETIRAR revisados por Alberto) y §0.E (3), aplicados en s324c
    rec0de = sorted((ROOT / "evals").glob("s324c_lote_0de_aplicar_*.json")); rec0de = rec0de[-1].name if rec0de else None
    if rec0de:
        for f in tri["seccion_0b_retirar_en_bloque"]:
            est_id[f["id"]] = "✅ RETIRADO del draft (artefacto; tu OK del 16-ago): no se crea"
        est_id["fidegas:el-11"] = "✅ RESUELTO: EL-11 no se crea (era «el 11/2018»); tus modelos S/3-2 y S/3-IR + S/2-IR DADOS DE ALTA con doc_map y retag del pm · recibo `" + rec0de + "`"
        est_id["morley:de-80"] = "✅ RESUELTO: DE-80 no se crea; TG confirmado como SOFTWARE (`notifier:tg`, alias TG-HONEYWELL; gate léxico PASS: 0 disparos en 96 consultas reales) · FAQ → doc_map + retag pm"
        est_id["notifier:etdt-312"] = "✅ RETIRADO + documento ETDT312 retirado del corpus (tu nota)"
        est_id["notifier:etdt-314"] = "✅ RETIRADO + documento ETDT314 retirado del corpus (tu nota)"
        est_id["notifier:madt-742"] = "✅ RETIRADO + documento MADT742 retirado del corpus (tu nota)"
        est_id["notifier:mndt-1202"] = "✅ RETIRADO + documento MNDT1202 retirado del corpus (tu nota)"
        est_id["notifier:madt-731"] = "✅ RETIRADO; MADT731_06 → doc_map `notifier:laserstar-hssd-2` (= HSSD-2, tu adjudicación con URL) + retag pm"
        est_id["notifier:madt-015"] = "⏳ PENDIENTE DE TI — el texto no nombra el modelo; sus hermanas MADT015_02/_03 ya están mapeadas a NFS8REL/NFS2-8 ⇒ ¿NFS2-8 (no FS2)? FS2-1/2/4 no existen en catálogo"
        est_id["notifier:mndt-600"] = "⏳ PENDIENTE DE TI — texto genérico (notas de calibración de detectores de gas), sin modelos; en corpus NO hay «SMART3 GD3/GD2» con esa grafía, SÍ la familia SMART 3 (EXPLOSIVOS/TOXICOS/3G ZONA 2, MNDT646) y en catálogo SMART3G-D3 (¿= GD3?). ¿MNDT600 → familia SMART 3 (paraguas nuevo)?"
        est_id["notifier:mndt-701"] = "⏳ PENDIENTE — «Software del detector de llamas Triple IR — SPECTRONIX (sharpEye)»: el software no tiene nombre en el texto y la familia SharpEye 20/20 (IR3) no está en catálogo → sin atestar hasta que exista el id"
        est_doc["asd in rail transportation applications_es"] = "✅ RETIRADO del corpus (tu nota §0.E)"
        est_doc["compatibilidad-entre-equipos-notifier-y-morley"] = "✅ MANTENER (tu nota): sin producto que mapear; la FAQ sigue en el corpus y es servible por retrieval para «¿equipos Notifier en central Morley?»"
        est_doc["d686 ema1224b4r_w ns4r"] = "✅ APLICADO (tu «aplica a EMA1224B4R/W»): alta `notifier:ema1224b4r-w` + doc_map + retag pm EN-54-3 → EMA1224B4R/W · recibo `" + rec0de + "`"
    t = E1.read_text(encoding="utf-8")
    # UNA sola pasada (la segunda llamada borraba las marcas de la primera) y claves normalizadas
    # (source_file de la DB lleva .pdf y mayúsculas; la casilla del packet, el slug en minúsculas)
    est_todo = {re.sub(r"\.pdf$", "", k.lower()): v for k, v in est_doc.items()}
    est_todo.update(est_id)
    t, n_todo = marcar(t, est_todo, r"[^`]+")
    n_doc = sum(1 for k in est_todo if ":" not in k and re.search(r"^- \[ \] `" + re.escape(k) + r"(\.pdf)?`", t, re.M | re.I))
    n_id = n_todo - n_doc
    pend_r1 = plan.get("pendiente_alberto_R1prima", [])
    cuerpo = f"""> ## 🟢 ESTADO s324 ({utc}) — lo que ya NO tienes que decidir, y lo que sí
> **Aplicado con recibo `{recibo}`** (dúo r32 Sol+Fable antes de escribir; verificación posterior en censo PASS):
> - **§0.A** (49) ✅ · **§0.B** (38 limpias + 4 «tu ojo» + tus anotaciones) ✅ **APLICADO** — {sum(1 for r in plan['doc_map_altas'] if r['reglas'][0].startswith('§0.B'))} filas doc_map.
> - **§1.A** (13): 13/13 resueltas por tus REGLAS R1/R1'/R2/R4/R5 (`evals/s324_reglas_residuo_adjudicacion_v1.json`).
> - **§1.B** (84): las de R6 (7) y R7 (23+4) están RESUELTAS con prueba (altas aplicadas o descartadas); acrónimos cortos (17) y confianza media (14) siguen en cuarentena; todo marcado fila a fila.
> - Retirados del corpus: MA-DT-1160 (tu adjudicación) + 6 fragmentos PT con hermano ES.
>
> **PENDIENTE DE TI (lo único que queda en este fichero):**
> 1. ~~**R1'**~~ — **firmada («R1' OK», 16-ago) y APLICADA**: {len(pend_r1)} docs, {sum(len(p['R1prima_cenida']) for p in pend_r1)} entries (recibo `s324b_r1prima_aplicar_*.json`).
> 2b. ~~**§0.D**~~ ~~**§0.E**~~ — **REVISADOS por ti y APLICADOS** (16-ago): 17 artefactos no creados; 5 documentos retirados del corpus (ETDT312/314, MADT742, MNDT1202, ASD Rail); altas S/3-2, S/3-IR, S/2-IR, EMA1224B4R/W; TG confirmado como software; MADT731_06 → HSSD-2; 5 retags de pm sucio. Quedan 3 preguntas tuyas (MADT015_01, MNDT600, MNDT701 — marcadas ⏳ en sus filas).
> 2. ~~**§0.C**~~ — **REVISADO por ti y APLICADO** (16-ago; tus 10 notas consolidadas bajo cada fila con mi respuesta `↳ s324b`; revisor Fable 6 hallazgos aplicados): 21 altas + 7 alias + 26 filas doc_map + 2 bajas de corpus (Vision Supra idiomas, MADT190P PT), recibo `s324b_lote_0c_aplicar_*.json`. Quedan DOS preguntas tuyas de §0.C (paraguas «2X-A» y STRATOS, marcadas ⏳ en sus filas) y **§0.D** (17 retirar) · **§0.E** (3).
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
> - **✅ Bloque «detnov» de §0.A APLICADO** (tu «confirmo que es modelo, y también los otros», 16-ago noche): CCD-102/104/108/112, CAD-250B, CAD-250-BLED confirmados; SGD-151 y SCD-250 como SOFTWARE (tu nota); CCD-103 → `detnov:ccd-103` (antes `unresolved`, candidate). El gate cazó lo que r30 avisaba: confirmar activaba alias descriptivos («2 zonas», «Conventional panels with 2 detection zones»…) que disparaban en consultas genéricas → 14 alias retirados ANTES. Recibo `s324c_e1b_detnov_aplicar_*.json`.
> - **Los demás bloques** (notifier, unresolved, systemsensor, xtralis, §0.B, §0.C, §0.D): planes + dry-run con censo PREPARADOS esta noche (`evals/s324c_e1b_bloques_censo_v1.md`) para que des el sí con el resultado del gate delante. NADA aplicado.
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
