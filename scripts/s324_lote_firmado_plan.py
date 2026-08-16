# -*- coding: utf-8 -*-
"""s324 — PLAN mecánico del LOTE FIRMADO (solo lectura: NO escribe catálogo ni Supabase).

Convierte en filas de escritura VERIFICADAS lo que Alberto firmó:
  · s323 §0.B (38 limpias con la regla serie × categoría + 4 «piden tu ojo» adjudicadas +
    sus anotaciones: ampliar ZX en dos FAQ de DXc, mndt1160 → ExitPoint, ds_kidde_2x_at_fr_s
    → repetidor 2X-AT-FR-S, guía 2X-A → FAMILIA 2X-A);
  · s324 R1..R7 sobre el residuo E1 §1 (`evals/s324_reglas_residuo_adjudicacion_v1.json`).

Cada fila lleva su VERIFICACIÓN contra el texto COMPLETO del documento en `chunks_v2`
(espacios normalizados): la cita debe ser subcadena; cada producto nuevo o confirmado debe
aparecer como TOKEN EXACTO en el documento que lo sustenta. Lo que no verifica NO entra en el
plan de escritura: cae a `no_aplicar` con su motivo. La escritura la hace
`scripts/s324_lote_firmado_writer.py` (dry-run / --aplicar), después del censo del radio de
explosión y del dúo.

Salida: evals/s324_lote_firmado_plan_v1.json
"""
from __future__ import annotations
import json, os, re, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto
from src.rag.catalog_store import CATALOG_DIR, _read_jsonl, norm_token

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
ADDED_BY = "s324-reglas"
REGLAS = "evals/s324_reglas_residuo_adjudicacion_v1.json"
PROV_R = ("s324 {regla} (regla adjudicada por Alberto 16-ago-2026, " + REGLAS +
          ") — {detalle}")

# ───────────────────────── catálogo ─────────────────────────
P = {r["id"]: r for r in _read_jsonl(CATALOG_DIR / "products.jsonl")}
U = {u["termino"]: u for u in _read_jsonl(CATALOG_DIR / "umbrellas.jsonl")}
A = _read_jsonl(CATALOG_DIR / "aliases.jsonl")
DM = _read_jsonl(CATALOG_DIR / "doc_map.jsonl")
DM_por_sf = {r["source_file"].lower(): r for r in DM}
DM_por_id = {r["document_id"]: r for r in DM}


def consumible(pid: str) -> bool:
    p = P.get(pid)
    return bool(p) and p.get("estado") == "activo" and not p.get("candidate")


def cat_de(pid: str) -> str | None:
    return ((P.get(pid) or {}).get("clasificacion") or {}).get("categoria")


def miembros(prefijo_id: str, categorias: set[str]) -> list[str]:
    return sorted(pid for pid in P if pid.startswith(prefijo_id) and consumible(pid)
                  and cat_de(pid) in categorias)


ZX_CENTRALES = sorted(set(U["ZXe"]["ids"]) | set(U["ZXSe"]["ids"]))       # 7 (gt s78/s90)
ZX_ALBERTO_DXC_FAQ = ["morley:zxae", "morley:zxee", "morley:zx2e", "morley:zx5e",
                      "morley:zx2se", "morley:zx5se"]                     # «ZX-A, ZX-E, ZX-2/5e, ZX2/5SE»
FAAST = list(U["FAAST"]["ids"])                                           # 13 (DEC-083)
DX_MODELOS = ["morley:dx1e", "morley:dx2e", "morley:dx4e"]
DX_CAJAS = ["morley:dx1e-20s", "morley:dx1e-40m", "morley:dx2e-40m", "morley:dx4e-40l"]
DXC = ["morley:dxc1", "morley:dxc2", "morley:dxc4"]
RP1R_CENTRALES = ["notifier:rp1r-supra", "notifier:rp1r", "morley:vsn-rp1r", "morley:vsn-rp1r-plus2"]
VSN_PLUS = ["morley:vsn-4-plus", "morley:vsn-8-plus", "morley:vsn-12-plus"]
X2A = miembros("kidde:2x-a", {"central", "repetidor"})   # incluye los 2x-at-*; excluye 2x-a-lb (accesorio) y la etiqueta 2x-at
X2AT = [pid for pid in X2A if pid.startswith("kidde:2x-at-")]
KE_DP312X = ["kidde:ke-dp3120w-sn", "kidde:ke-dp3120w-snv", "kidde:ke-dp3121b-snv",
             "kidde:ke-dp3121w", "kidde:ke-dp3121w-sn", "kidde:ke-dp3121w-snv"]

# ───────────────────────── Supabase (lectura) ─────────────────────────
_docs: dict[str, dict] = {}
_text: dict[str, str] = {}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def doc(c, nombre: str) -> dict | None:
    if nombre in _docs:
        return _docs[nombre]
    r = c.get(f"{SB}/rest/v1/documents", headers=HS,
              params={"select": "id,source_pdf_filename,status,product_model,manufacturer",
                      "source_pdf_filename": f"eq.{nombre}"})
    r.raise_for_status()
    rows = r.json()
    if len(rows) != 1:   # tolerancia a mayúsculas/extensión
        r = c.get(f"{SB}/rest/v1/documents", headers=HS,
                  params={"select": "id,source_pdf_filename,status,product_model,manufacturer",
                          "source_pdf_filename": f"ilike.{nombre}*"})
        rows = [x for x in r.json() if x["status"] == "active"] if r.status_code == 200 else []
    _docs[nombre] = rows[0] if len(rows) == 1 else None
    return _docs[nombre]


def texto(c, doc_id: str) -> str:
    if doc_id in _text:
        return _text[doc_id]
    out, off = [], 0
    while True:
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "chunk_index,content", "document_id": f"eq.{doc_id}",
                          "order": "chunk_index.asc", "offset": str(off), "limit": "500"})
        r.raise_for_status()
        rows = r.json()
        out += [x["content"] or "" for x in rows]
        if len(rows) < 500:
            break
        off += 500
    _text[doc_id] = _norm(" ".join(out))
    return _text[doc_id]


def n_token(txt: str, tok: str) -> int:
    rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(tok) + r"(?![A-Za-z0-9-])", re.I)
    return len(rx.findall(txt))


def cita_ok(txt: str, cita: str) -> bool:
    c = _norm(cita).strip("«»\" ")
    return bool(c) and c[:200] in txt


def ventana(txt: str, tok: str, ancho: int = 90) -> str:
    """Cita verbatim (≤200 chars, espacios normalizados) alrededor del token exacto: de todas
    las apariciones se elige la ventana con MÁS letras (evita separadores de tabla y
    direcciones) y se recorta a límites de palabra."""
    rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(tok) + r"(?![A-Za-z0-9-])", re.I)
    mejor, mejor_score = "", -1.0
    for m in rx.finditer(txt):
        a, b = max(0, m.start() - ancho), min(len(txt), m.end() + ancho)
        w = txt[a:b]
        letras = sum(ch.isalpha() for ch in w)
        score = letras / max(1, len(w)) + (0.3 if "#" in w[:ancho] else 0.0)
        if score > mejor_score:
            mejor, mejor_score = w, score
    if not mejor:
        return ""
    # recorte a límites de palabra por ambos lados (sigue siendo subcadena verbatim)
    mejor = re.sub(r"^\S*\s", "", mejor, count=1) if not mejor.startswith(("#", "*")) else mejor
    mejor = re.sub(r"\s\S*$", "", mejor, count=1)
    return mejor[:200]


# ───────────────────────── plan ─────────────────────────
plan = {"que_es": __doc__.strip().splitlines()[0], "utc": None, "reglas": REGLAS,
        "constantes": {"ZX_CENTRALES": ZX_CENTRALES, "FAAST": FAAST, "DX_MODELOS": DX_MODELOS,
                       "RP1R_CENTRALES": RP1R_CENTRALES, "VSN_PLUS": VSN_PLUS, "X2A": X2A, "X2AT": X2AT},
        "doc_map_altas": [], "doc_map_modificaciones": [], "products_altas": [],
        "products_confirmar": [], "products_retirar": [], "aliases_quitar": [],
        "umbrellas_altas": [], "retags_db": [], "no_aplicar": [], "avisos": []}


def entrada(doc_row, ids, regla, cita, detalle, verif, role="primary"):
    return {"document_id": doc_row["id"], "source_file": doc_row["source_pdf_filename"],
            "entries": [{"id": i, "role": role, "scope": "doc",
                         "provenance": PROV_R.format(regla=regla, detalle=detalle)} for i in ids],
            "regla": regla, "cita": cita, "verificacion": verif}


def main() -> None:
    v3 = json.loads((ROOT / "evals/s323_tierb_v3_serie_x_categoria.json").read_text(encoding="utf-8"))
    tierb = json.loads((ROOT / "evals/s322f_e1s2_tierb_docmap_v1.json").read_text(encoding="utf-8"))
    tb_por_sf = {f["source_file"].lower(): f for f in tierb["seccion_0_bloque"] + tierb["seccion_1_individual"]}
    triage = json.loads((ROOT / "evals/s322g_e1_candidatos_triage_v1.json").read_text(encoding="utf-8"))

    with abierto(timeout=60.0) as c:
        # ═══ A1 · §0.B limpias (v3) con las anotaciones de Alberto ═══
        overrides = {
            "ma-dt-1160": None,                                    # retirado (s324_retirar_docs)
            "mndt1160": ["systemsensor:pf24v"],                   # Alberto: «el modelo es ExitPoint» → en catálogo ExitPoint ES pf24v (alias EXITPOINT; I56-2961: «EXITPOINT — PF24V Directional Sounder»)
            "con-que-sistema-operativo-es-compatible-el-programa-de-la-dxc-connexion": DXC + ZX_ALBERTO_DXC_FAQ,
            "morley-se-pueden-pasar-programaciones-de-zx-y-dimension-a-connexion-dxc": DXC + ZX_CENTRALES + DX_MODELOS,
        }
        for f in v3["limpias"]:
            sf = f["documento"]
            key = sf.lower()
            tb = tb_por_sf.get(key)
            if not tb:
                plan["no_aplicar"].append({"que": sf, "motivo": "sin fila en el recibo tier B (no hay document_id)"}); continue
            ids = f.get("ids_por_serie_x_categoria") or f["ids_originales"]
            regla, detalle = "§0.B", f["motivo"]
            for k, v in overrides.items():
                if key.startswith(k) or key == k:
                    if v is None:
                        ids = None
                    else:
                        ids, regla = v, "§0.B+Alberto"
                        detalle = "anotación de Alberto en el packet (s323) sobre la fila limpia"
            if ids is None:
                plan["no_aplicar"].append({"que": sf, "motivo": "documento RETIRADO en s324 (adjudicación s323)"}); continue
            d = doc(c, sf) or {"id": tb["document_id"], "source_pdf_filename": tb["source_file"], "status": "?"}
            txt = texto(c, d["id"])
            ok = cita_ok(txt, f["cita"])
            faltan = [i for i in ids if i not in P]
            verif = {"cita_full_text": ok, "n_chunks_texto": len(txt) > 0,
                     "ids_inexistentes_hoy": faltan,
                     "ids_pendientes_de_este_lote": [i for i in ids if i in DX_MODELOS]}
            if not ok:
                plan["no_aplicar"].append({"que": sf, "motivo": "cita NO verifica full-text hoy", "cita": f["cita"]}); continue
            if verif["ids_inexistentes_hoy"]:
                plan["no_aplicar"].append({"que": sf, "motivo": f"ids inexistentes {verif['ids_inexistentes_hoy']}"}); continue
            plan["doc_map_altas"].append(entrada(d, ids, regla, f["cita"], detalle, verif))

        # ═══ A2 · §0.B.2 (4 «piden tu ojo», adjudicadas) ═══
        ojo = {
            "dxc_guia de usuario_multiling": (DXC, "Alberto: OK (serie DX Connexion × central)"),
            "hd_ke_dt3101w_hab_202407_es_30e0": (["kidde:ke-dt3101w-hab"], "Alberto: OK (serie Excellence × detector; documento de producto)"),
            "hlsi-ti-001": (RP1R_CENTRALES, "Alberto: misma adjudicación que HLSI-TI-001 + «también aplica a la VSN-RP1r+» → serie RP1r × central de extinción (rp1r-supra, rp1r, vsn-rp1r, vsn-rp1r-plus2; OPC-RP1r software excluido)"),
            "00-3280-508-4009-03_r003_2x-a_series_quick_operation_guide_es": (X2A, "Alberto (437ee3f): la guía es de la FAMILIA 2X-A → serie 2X-A × {central, repetidor}; 2X-A-LB (accesorio) fuera"),
        }
        for f in v3["piden_tu_ojo"]:
            sf = f["documento"]; key = sf.lower()
            hit = next((k for k in ojo if key.startswith(k)), None)
            if not hit:
                plan["no_aplicar"].append({"que": sf, "motivo": "§0.B.2 sin adjudicación registrada"}); continue
            ids, detalle = ojo[hit]
            d = doc(c, sf) or {"id": tb_por_sf[key]["document_id"], "source_pdf_filename": tb_por_sf[key]["source_file"], "status": "?"}
            txt = texto(c, d["id"])
            ok = cita_ok(txt, f["cita"])
            plan["doc_map_altas"].append(entrada(d, ids, "§0.B.2+Alberto", f["cita"], detalle,
                                                 {"cita_full_text": ok, "n_ids": len(ids)}))
            if not ok:
                plan["avisos"].append({"que": sf, "aviso": "cita §0.B.2 no verifica full-text hoy (se mantiene: adjudicación explícita de Alberto)"})

        # ═══ A3 · §1.A residuo doc_map por reglas ═══
        r1a = [
            ("996-130-000-3 manuel d'utilisation zx_hlsi", ZX_CENTRALES, "R1", "serie ZX × central (paraguas gt ZXe+ZXSe); doc FR de 1 chunk — ver aviso"),
            ("con-que-sistema-operativo-es-compatible-el-programa-de-la-zx-y-dx", ZX_CENTRALES + DX_MODELOS, "R1", "FAQ de las familias ZX y DX (Dimension) → serie × central"),
            ("asd harsh environments_sp", FAAST, "R1", "guía de aplicación de la FAMILIA FAAST (paraguas gt, 13 miembros); el doc no nombra ningún modelo"),
            ("finales-de-linea-de-las-centrales-convencionales", ["notifier:nfs-2-8", "morley:vsn2-lt", "morley:vsn4-lt", "morley:vsn8-lt", "morley:vsn12-lt"] + VSN_PLUS, "R1+R2", "FAQ: NFS2-8, familia VSN-LT, familia VSN-PLUS (4/8/12 según MIEMI130; vsn-12-plus se confirma en este lote); VSN2-PLUS queda candidate → fuera"),
            ("gr_kidde_2x_at_fr_fb_s_27cf", X2AT, "R1", "«2X-AT Series Quick Start Guide» → sub-familia 2X-AT × {central, repetidor} (11); la etiqueta kidde:2x-at NO se promueve (R2: paraguas)"),
            ("hlsi-ti-007_vsn-4rel", ["notifier:vsn-4rel"], "R5", "Alberto: «el modelo es VSN-4REL» (módulo de 4 relés NFS-SUPRA/RP1R-SUPRA, notifier.es); contenido ingestado = 47 chars → atestación por ficha + re-ingesta OCR pendiente"),
            ("mi_kidde_2x_at_f2_fb_07d4", X2A, "R1", "«installation manual for the 2X-A Series fire alarm, repeater and evacuation panels» → familia 2X-A × {central, repetidor}"),
            ("mu_kidde_2x_at_fr_fb_s_6c31", X2A, "R1", "«2X-A Series Operation Manual» → familia 2X-A × {central, repetidor}"),
            ("mi_kidde_ke_dp312x_snx_202512_es_242d", KE_DP312X, "R4", "hoja de instalación de las variantes con sirena/VAD; los 6 nombrados (token exacto 3-8 chunks) se dan de alta en este lote; KE-DP3120W (0 tokens) no se atesta"),
            ("mi_kidde_ke_io3144_631e", ["kidde:ke-io3122", "kidde:ke-io3144"], "R4", "el contenido nombra KE-IO3122 ×8 y KE-IO3144 ×8; KE-IU3110 ×0 (etiqueta errónea → retag en F)"),
        ]
        for sf, ids, regla, detalle in r1a:
            tb = tb_por_sf.get(sf.lower())
            d = doc(c, sf) or (tb and {"id": tb["document_id"], "source_pdf_filename": tb["source_file"], "status": "?"})
            if not d:
                plan["no_aplicar"].append({"que": sf, "motivo": "documento no localizado"}); continue
            txt = texto(c, d["id"])
            cita = ((tb or {}).get("llm") or {}).get("cita") or ""
            verif = {"cita_full_text": cita_ok(txt, cita) if cita else None,
                     "tokens_en_doc": {i: n_token(txt, P[i]["canonical_model"]) for i in ids if i in P}}
            plan["doc_map_altas"].append(entrada(d, ids, regla, cita, detalle, verif))
        plan["avisos"].append({"que": "996-130-000-3 manuel d'utilisation zx_hlsi",
                               "aviso": "fragmento FRANCÉS de 1 chunk (páginas finales); misma clase que los PT retirados (política s65) pero SIN sí de Alberto para FR → se atesta por R1 y se propone baja aparte"})

        # ═══ B · products ALTAS (R4 + R7 componentes + ExitPoint) ═══
        CANON = {}
        for _pid, _p in P.items():
            CANON.setdefault(norm_token(_p.get("canonical_model") or ""), _pid)

        def alta(pid, canonical, doc_name, tokens_extra=(), familia=None, vb=None, regla="R7", detalle=""):
            d = doc(c, doc_name)
            if not d:
                plan["no_aplicar"].append({"que": pid, "motivo": f"doc {doc_name!r} no localizado"}); return None
            txt = texto(c, d["id"])
            n = n_token(txt, canonical)
            cita = ventana(txt, canonical)
            if n == 0 or not cita:
                plan["no_aplicar"].append({"que": pid, "motivo": f"{canonical!r} NO aparece como token exacto en {doc_name!r} (regla {regla}: sin cita propia no hay alta)"}); return None
            existente = CANON.get(norm_token(canonical)) or (pid if pid in P else None)
            if existente:
                pe = P[existente]
                if pe.get("estado") == "activo" and pe.get("candidate"):
                    # ya existe como candidate: R2 (nombrado como sujeto con cita) → CONFIRMAR, no duplicar
                    plan["products_confirmar"].append({"id": existente, "canonical_model": pe["canonical_model"], "doc": d["source_pdf_filename"],
                                                       "document_id": d["id"], "n_token": n, "cita": cita,
                                                       "provenance_add": PROV_R.format(regla="R2 (vía " + regla + ")", detalle=f"nombrado como sujeto en {d['source_pdf_filename']} ({n} chunks); cita: «{cita}»")})
                    plan["avisos"].append({"que": pid, "aviso": f"el catálogo ya tenía {existente!r} (candidate) con la misma grafía normalizada → se CONFIRMA en vez de duplicar"})
                elif pe.get("estado") == "activo":
                    plan["avisos"].append({"que": pid, "aviso": f"ya existe {existente!r} activo con esa grafía → solo doc_map"})
                else:
                    plan["no_aplicar"].append({"que": pid, "motivo": f"existe {existente!r} en estado {pe.get('estado')}: no se recicla ni duplica"}); return None
                plan["doc_map_altas"].append(entrada(d, [existente], regla, cita, f"documento que nombra {canonical} ({n} chunks); id existente", {"token_exacto": n}))
                return {"id": existente, "existente": True}
            marca = vb or (["Kidde Commercial"] if "KIDDE COMMERCIAL" in txt.upper() and d["manufacturer"] in ("Kidde", "Aritech") else [d["manufacturer"]])
            row = {"id": pid, "canonical_model": canonical, "estado": "activo", "candidate": False,
                   "vendido_bajo": marca, "added_by": ADDED_BY,
                   "provenance": PROV_R.format(regla=regla, detalle=f"cita verificada full-text en {d['source_pdf_filename']} ({n} chunks con el token); {detalle}").strip("; ")}
            if familia:
                row["familia"] = familia
            plan["products_altas"].append({"row": row, "doc": d["source_pdf_filename"], "document_id": d["id"],
                                           "cita": cita, "n_token": n, "regla": regla})
            # doc_map del documento sustentante → el producto nuevo
            plan["doc_map_altas"].append(entrada(d, [pid], regla, cita, f"documento que sustenta el alta de {canonical}",
                                                 {"token_exacto": n}))
            return row

        # R4 — familia KE-DP312x (base + variantes; base ya existe)
        for pid, cm in [("kidde:ke-dp3120w-sn", "KE-DP3120W-SN"), ("kidde:ke-dp3120w-snv", "KE-DP3120W-SNV"),
                        ("kidde:ke-dp3121b-snv", "KE-DP3121B-SNV"), ("kidde:ke-dp3121w", "KE-DP3121W"),
                        ("kidde:ke-dp3121w-sn", "KE-DP3121W-SN"), ("kidde:ke-dp3121w-snv", "KE-DP3121W-SNV")]:
            alta(pid, cm, "MI_KIDDE_KE_DP312x_SNx_202512_ES_242d.pdf", familia="KE-DP312x", regla="R4",
                 detalle="Alberto 16-ago: mini-familia KE-DP312x (base + variantes SN/SNV)")
        alta("kidde:ke-dp3121b", "KE-DP3121B", "HD_KE_DP3121B_202407_ES_8c51.pdf", familia="KE-DP312x", regla="R4",
             detalle="SKU base negro con hoja propia")
        # R7 — componentes con cita propia (cada uno se verifica en SU documento)
        r7 = [
            ("kidde:ke-dp3121b-snv", "KE-DP3121B-SNV", "DS_KIDDE_KE_DP3121B_SNV_202503_ES_b5bc.pdf"),   # ya creado arriba → doc_map extra
            ("kidde:ke-dp3121w-sn", "KE-DP3121W-SN", "DS_KIDDE_KE_DP3121W_SN_202503_ES_5938.pdf"),
            ("kidde:ke-dp3121w-snv", "KE-DP3121W-SNV", "DS_KIDDE_KE_DP3121W_SNV_202503_ES_8699.pdf"),
            ("kidde:ke-dba-adpw-kil", "KE-DBA-ADPW-KIL", "G_INST_KIDDE_KE_DBA_ADPW_202502_ES_70e7.pdf"),
            ("kidde:ke-dba-adpw-zit", "KE-DBA-ADPW-ZIT", "G_INST_KIDDE_KE_DBA_ADPW_202502_ES_70e7.pdf"),
            ("kidde:ke-dba-labw-l1s", "KE-DBA-LABW-L1S", "HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf"),
            ("kidde:ke-dba-labw-l2s", "KE-DBA-LABW-L2S", "HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf"),
            ("kidde:ke-dba-labw-l3s", "KE-DBA-LABW-L3S", "HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf"),
            ("kidde:ke-dba-labw-l4s", "KE-DBA-LABW-L4S", "HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf"),
            ("kidde:ke-iu3111-zme", "KE-IU3111-ZME", "DS_KIDDE_KE_IU3111_ZME_f908.pdf"),
            ("kidde:ke-iu3111-zme", "KE-IU3111-ZME", "MI_KE_IU3111_ZME_202407_ES_fde1.pdf"),
            ("kidde:n-io-mbx-1", "N-IO-MBX-1", "DS_KIDDE_N_IO_MBX_1_202505_ES_07ca.pdf"),
            ("kidde:n-io-mbx-1", "N-IO-MBX-1", "MI_N_IO_MBX_X_202505_ES__1__1fd1.pdf"),
            ("kidde:n-io-mbx-2", "N-IO-MBX-2", "MI_N_IO_MBX_X_202505_ES__1__1fd1.pdf"),
            ("kidde:n-io-sbx-1g", "N-IO-SBX-1G", "DS_KIDDE_N_IO_SBX_1G_202505_ES_b086.pdf"),
            ("kidde:n-io-sbx-2g", "N-IO-SBX-2G", "DS_KIDDE_N_IO_SBX_1G_202505_ES_b086.pdf"),
            ("kidde:zlsm-me", "ZLSM-ME", "DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf"),
            ("kidde:zlsm-me", "ZLSM-ME", "MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf"),
            ("kidde:zlsm-mr", "ZLSM-MR", "DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf"),
            ("kidde:zlsm-mr", "ZLSM-MR", "MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf"),
            ("fidegas:s-3-t1", "S/3-T1", "Manual-de-Usuario-S3-T1-y-S-2-T1"),
            ("fidegas:s-2-t1", "S/2-T1", "Manual-de-Usuario-S3-T1-y-S-2-T1"),
            ("notifier:nx2-r-r", "NX2/R/R", "EMA24RS2R_NX2y5-R-R"),
            ("notifier:nx5-r-r", "NX5/R/R", "EMA24RS2R_NX2y5-R-R"),
        ]
        creados = {r["row"]["id"] for r in plan["products_altas"]}
        for pid, cm, dn in r7:
            if pid in creados or pid in P:
                # ya existe (creado en este lote o en catálogo): solo doc_map si el token verifica
                d = doc(c, dn)
                if d:
                    txt = texto(c, d["id"]); n = n_token(txt, cm)
                    if n:
                        plan["doc_map_altas"].append(entrada(d, [pid], "R7", ventana(txt, cm),
                                                             f"documento adicional que nombra {cm} ({n} chunks)", {"token_exacto": n}))
                    else:
                        plan["no_aplicar"].append({"que": f"doc_map {dn} → {pid}", "motivo": f"{cm!r} no aparece como token en {dn!r}"})
                continue
            fam = {"kidde:ke-dba-adpw": "KE-DBA-ADPW", "kidde:ke-dba-labw": "KE-DBA-LABW", "kidde:n-io-mbx": "N-IO-MBX",
                   "kidde:n-io-sbx": "N-IO-SBX", "kidde:zlsm": "ZLSM", "fidegas:s-": "S/x-T1", "notifier:nx": "NX/R/R"}
            familia = next((v for k, v in fam.items() if pid.startswith(k)), None)
            if alta(pid, cm, dn, familia=familia, regla="R7", detalle="componente de una grafía concatenada del draft E1 (§1.B), con cita propia"):
                creados.add(pid)
        # ExitPoint (adjudicación s323 de Alberto sobre mndt1160): NO se crea producto — el catálogo ya
        # modela ExitPoint como alias de systemsensor:pf24v y I56-2961 prueba «EXITPOINT — PF24V Directional
        # Sounder» (línea = ExitPoint, modelo = PF24V). El doc_map de MNDT1160 apunta al id pf24v = ExitPoint.
        plan["avisos"].append({"que": "mndt1160 → ExitPoint", "aviso": "ExitPoint es la LÍNEA y PF24V su modelo (I56-2961-000R: «EXITPOINT — PF24V Directional Sounder with Voice Messaging»); alias EXITPOINT→systemsensor:pf24v ya existe → el doc_map apunta a pf24v, que ES ExitPoint. No se crea producto duplicado."})

        # ═══ C · products CONFIRMAR (R2: modelos concretos nombrados como sujeto) ═══
        conf = [
            ("morley:dx1e", "DX1e", "MIE-MP-520rv04.pdf"), ("morley:dx2e", "DX2e", "MIE-MP-520rv04.pdf"),
            ("morley:dx4e", "DX4e", "MIE-MP-520rv04.pdf"),
            ("morley:dx1e-20s", "DX1e-20S", "MIE-MP-520rv04.pdf"), ("morley:dx2e-40m", "DX2e-40M", "MIE-MP-520rv04.pdf"),
            ("morley:dx4e-40l", "DX4e-40L", "MIE-MP-520rv04.pdf"),
            ("morley:vsn-12-plus", "VSN 12 PLUS", "MIEMI130.pdf"),
        ]
        for pid, cm, dn in conf:
            p = P.get(pid)
            if not p or not p.get("candidate"):
                plan["no_aplicar"].append({"que": pid, "motivo": "no es candidate hoy (nada que confirmar)"}); continue
            d = doc(c, dn); txt = texto(c, d["id"]) if d else ""
            n = n_token(txt, cm); cita = ventana(txt, cm)
            if not n:
                plan["no_aplicar"].append({"que": pid, "motivo": f"{cm!r} no aparece como token exacto en {dn!r}"}); continue
            plan["products_confirmar"].append({"id": pid, "canonical_model": cm, "doc": dn, "document_id": d["id"],
                                               "n_token": n, "cita": cita,
                                               "provenance_add": PROV_R.format(regla="R2", detalle=f"modelo concreto nombrado como sujeto en {dn} ({n} chunks); cita: «{cita}»")})

        # ═══ D · products RETIRAR (etiquetas de familia → paraguas) + alias/doc_map colgantes ═══
        for pid, motivo in [("kidde:2x-at", "etiqueta de sub-familia (2X-A Táctil); pasa a paraguas «2X-AT»"),
                            ("notifier:vsn-plus", "etiqueta de familia (VSN PLUS = 4/8/12 según MIEMI130); pasa a paraguas «VSN PLUS»")]:
            if pid in P and P[pid]["estado"] == "activo":
                plan["products_retirar"].append({"id": pid, "motivo": motivo, "estado_prev": P[pid]["estado"], "candidate_prev": P[pid].get("candidate")})
        for a in A:
            if a["id"] in ("kidde:2x-at", "notifier:vsn-plus"):
                plan["aliases_quitar"].append(a)
        # doc_map colgantes: la QOG 2X-AT apuntaba a la etiqueta → miembros; la FAQ RP1R pierde vsn-plus (y un duplicado)
        for r in DM:
            ids = [e["id"] for e in r["entries"]]
            if "kidde:2x-at" in ids:
                plan["doc_map_modificaciones"].append({"document_id": r["document_id"], "source_file": r["source_file"],
                                                       "entries_prev": ids, "entries_nuevas": X2AT,
                                                       "regla": "R1", "detalle": "la QOG «2X-AT Series» apuntaba a la etiqueta; ahora a los 11 miembros de la sub-familia"})
            if "notifier:vsn-plus" in ids:
                nuevas = []
                for e in r["entries"]:
                    if e["id"] == "notifier:vsn-plus" or e["id"] in {x["id"] for x in nuevas}:
                        continue
                    nuevas.append(e)
                plan["doc_map_modificaciones"].append({"document_id": r["document_id"], "source_file": r["source_file"],
                                                       "entries_prev": ids, "entries_nuevas": [e["id"] for e in nuevas],
                                                       "regla": "R2", "detalle": "se quita la etiqueta vsn-plus (y una entry duplicada); qué modelo VSN PLUS trata la FAQ queda abierto (VSN2-PLUS/PLUS2 solo en docs NFS-SUPRA)"})

        # ═══ E · umbrellas (listas planas de ids de producto; adjudicadas → candidate=false) ═══
        def umb(termino, tipo, ids, prov, diferido=None):
            row = {"termino": termino, "tipo": tipo, "ids": ids, "divergent": True,
                   "candidate": False, "added_by": ADDED_BY, "provenance": prov}
            if diferido:
                row["diferido"] = diferido
            plan["umbrellas_altas"].append(row)
        umb("2X-A", "familia", X2A, "Alberto s323 (437ee3f): alta de la FAMILIA 2X-A; miembros DERIVADOS por regla prefijo 2X-A × categoría {central, repetidor} (2X-A-LB accesorio fuera) — s324",
            diferido="gate léxico s324 (censo del radio de explosión): el core «2·x·a» del término DISPARA en el negativo sintético «2 x a» (normkey 3 chars). Lo adjudicado por Alberto (la guía → familia) ya lo cubre R1 vía doc_map a los miembros; el paraguas es modelado del autor → se somete al dúo antes de crearlo. El writer lo SALTA.")
        umb("2X-AT", "serie", X2AT, "Alberto s324 (16-ago): 2X-AT = sub-familia táctil de la 2X-A → apunta a sus modelos; derivados por prefijo 2X-AT- × {central, repetidor}")
        umb("2X-A Táctil", "serie", X2AT, "sinónimo de «2X-AT» (product_model de las guías rápidas); mismos miembros — s324")
        umb("VSN PLUS", "familia", VSN_PLUS, "Alberto s324 (16-ago): VSN-Plus tiene los modelos VSN 4 PLUS, VSN 8 PLUS, VSN 12 PLUS según MIEMI130")
        if "VSN PLUS" in {norm_token(k): k for k in U} or norm_token("VSN PLUS") in {norm_token(k) for k in U}:
            plan["avisos"].append({"que": "VSN PLUS", "aviso": "ya existe un paraguas con ese término normalizado"})

        # ═══ F · retags DB (documents.product_model + chunks_v2.product_model, CAS por chunk) ═══
        for dn, pm_prev, pm_nuevo, motivo in [
            ("4188-1132-ES issue 3_04_2025_Qref", "CLSS-10", "INSPIRE E10/E15", "la Qref ES estaba etiquetada CLSS-10 (pasarela cloud, 9 chunks) pero nombra INSPIRE ×13 / E10 ×11; doc_map ya apunta a inspire-e10/e15"),
            ("MI_KIDDE_KE_IO3144_631e.pdf", "KE-IO3144/KE-IU3110", "KE-IO3122/KE-IO3144", "KE-IU3110 no aparece en el contenido; el doc trata KE-IO3122 y KE-IO3144 (Alberto 16-ago)"),
        ]:
            d = doc(c, dn)
            plan["retags_db"].append({"document_id": d["id"], "source_file": dn, "pm_prev": pm_prev, "pm_nuevo": pm_nuevo,
                                      "documents_pm_actual": d["product_model"], "motivo": motivo})

        # ═══ G · NO aplicar (con motivo) — R6 y clases que esperan a Alberto o a otra puerta ═══
        for r in triage["seccion_1_individual"]:
            m = r["motivos_individual"] or ["<sin motivo>"]
            m0 = m[0]
            if "no-activo" in m0:
                plan["no_aplicar"].append({"que": r["id"], "motivo": f"R6: única fuente {r['documento']['source_pdf_filename']!r} está {r['documento']['status']} → NO se da de alta"})
            elif "termino-multi-modelo" in m0 and not (r["llm"].get("termino_real")):
                plan["no_aplicar"].append({"que": r["id"], "motivo": "nombre de producto CON barra (no concatenación): R7 no aplica; PRODUCTO_REAL pendiente del sí de Alberto (clase §0.C)", "canonical_model": r["canonical_model"], "doc": r["documento"]["source_pdf_filename"]})
            elif "acronimo-corto" in m0:
                plan["no_aplicar"].append({"que": r["id"], "motivo": "riesgo léxico (acrónimo corto): Puerta A / predicado de reconstruibilidad (tarea 4)"})
            elif "confianza-media" in m0:
                plan["no_aplicar"].append({"que": r["id"], "motivo": "confianza media: re-juicio K=5 cross-model (tarea 6)"})

    # ═══ MERGE · una fila de doc_map por document_id (el validador exige unicidad) ═══
    fusion: dict[str, dict] = {}
    for e in plan["doc_map_altas"]:
        f = fusion.get(e["document_id"])
        if not f:
            f = fusion[e["document_id"]] = {"document_id": e["document_id"], "source_file": e["source_file"],
                                             "entries": [], "reglas": [], "citas": [], "verificaciones": []}
        vistos = {x["id"] for x in f["entries"]}
        for x in e["entries"]:
            if x["id"] not in vistos:
                f["entries"].append(x); vistos.add(x["id"])
        f["reglas"].append(e["regla"]); f["citas"].append(e["cita"]); f["verificaciones"].append(e["verificacion"])
    plan["doc_map_altas_sin_fusionar"] = len(plan["doc_map_altas"])
    plan["doc_map_altas"] = list(fusion.values())
    # cada cita de las altas de producto debe seguir siendo subcadena del texto (auto-check)
    plan["autocheck_citas_altas"] = all(r["cita"] and r["cita"] in _text[r["document_id"]] for r in plan["products_altas"])
    plan["autocheck_citas_confirmar"] = all(r["cita"] and r["cita"] in _text[r["document_id"]] for r in plan["products_confirmar"])

    plan["utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plan["resumen"] = {k: len(v) for k, v in plan.items() if isinstance(v, list)}
    out = ROOT / "evals" / "s324_lote_firmado_plan_v1.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(plan["resumen"], ensure_ascii=False))
    for x in plan["no_aplicar"]:
        print("  NO:", x["que"], "—", x["motivo"][:110])
    for x in plan["avisos"]:
        print("  AVISO:", x["que"], "—", x["aviso"][:110])
    print("plan:", out.relative_to(ROOT))


if __name__ == "__main__":
    main()
