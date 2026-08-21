# -*- coding: utf-8 -*-
"""s331 — Genera el plan del LOTE §1.A+§1.B (anotaciones de Alberto en el packet E1).

Post-dúo r40. Lo que el dúo dejó FUERA está en `no_aplicar`, con su motivo.
Uso:  python scripts/s331_lote_1AB_generar.py   → evals/s331_lote_1AB_plan_v1.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
FIRMA = ("s331 §1.A+§1.B — anotaciones de Alberto en el packet E1 (20-ago-2026), verificadas una a una; "
         "dúo r40 aplicado antes de escribir")

# id → (canonical, pdf del documento que lo nombra, marca, nota)
ALTAS = [
    ("kidde:ke-dba-labw-s", "KE-DBA-LABW-S", "HD_KE_DBA_LABW_LxS_202407_ES_2fc1.pdf", ["Kidde Commercial"],
     "«OK con juez» de Alberto: R7 no pudo partir L1S..L4S (no aparecen como token); el sujeto real del "
     "documento es KE-DBA-LABW-S, en el título"),
    ("notifier:conv232-485", "CONV232/485", "TIDT110.pdf", ["Notifier"],
     "«el modelo es CONV232/485» (Alberto): referencia comercial en el título de la TI; RS232 y RS485/422 "
     "NO se dan de alta — son esquemas de transmisión, no modelos (matiz suyo)"),
    ("kidde:9-30520", "9-30520", "DS_KIDDE_ZLSM_ME_202604_ES_c3d9.pdf", ["Kidde Global Solutions"],
     "«OK con juez» de Alberto: ZLSM-ME/ZLSM-MR son artefactos (0 menciones) y R7 no los creó; el sujeto "
     "real es el P/N 9-30520, «Carcasa de expansión MiniLaser»"),
]
# doc extra que atesta el mismo producto (misma hoja en otro idioma)
DOCMAP_EXTRA = [("MI_KIDDE_ZLSM_ME_202604_ING_29a1.pdf", ["kidde:9-30520"],
                 "hoja de instalación en inglés del mismo accesorio («MiniLaser Expansion Housing»)")]
# MNDT730: miniguía de FAMILIA → los 3 miembros del paraguas STRATOS (R1), en simetría con MADT731_02
DOCMAP_STRATOS = ("MNDT730.pdf", ["notifier:laserstar-hssd-2", "notifier:minilser25", "notifier:minilaser-100"])
MOD_DXC = ("Con-que-Sistema-Operativo-es-compatible-el-programa-de-la-DXc-Connexion.pdf",
           ["morley:dxc1", "morley:dxc2", "morley:dxc4"])
MOD_ZXDX = ("Con-que-Sistema-Operativo-es-compatible-el-programa-de-la-ZX-y-DX.pdf",
            ["morley:zx10se", "morley:zx1e", "morley:zx1se", "morley:zx2e", "morley:zx2se",
             "morley:zx5e", "morley:zx5se", "morley:dx1e", "morley:dx2e", "morley:dx4e",
             "morley:zxae", "morley:zxee"])


def _get(c, path, **params):
    r = c.get(f"{SB}/rest/v1/{path}", headers=HS, params=params)
    r.raise_for_status()
    return r.json()


def main() -> int:
    with abierto(timeout=60.0) as c:
        docs, off = [], 0
        while True:                      # `documents` supera las 1000 filas: sin paginar se pierden docs
            page = _get(c, "documents", select="id,document_family,source_pdf_filename,status",
                        limit="1000", offset=str(off))
            docs += page
            if len(page) < 1000:
                break
            off += 1000
        por_pdf = {d["source_pdf_filename"]: d for d in docs if d["status"] == "active"}

        def cita(document_id: str, token: str) -> tuple[int, str]:
            rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])")
            chunks = _get(c, "chunks_v2", select="chunk_index,content",
                          document_id=f"eq.{document_id}", order="chunk_index")
            n, txt = 0, ""
            for ch in chunks:
                m = rx.search(ch["content"] or "")
                if m:
                    n += 1
                    if not txt:
                        ini = max(0, m.start() - 90)
                        txt = re.sub(r"\s+", " ", ch["content"][ini:m.end() + 90]).strip()
            return n, txt

        altas, docmap, faltan = [], [], []
        for pid, canon, pdf, marcas, nota in ALTAS:
            d = por_pdf.get(pdf)
            if not d:
                faltan.append({"id": pid, "motivo": f"documento {pdf} no activo"})
                continue
            n, txt = cita(d["id"], canon)
            if not n:
                faltan.append({"id": pid, "motivo": f"0 chunks con el token exacto «{canon}»"})
                continue
            altas.append({
                "row": {"id": pid, "canonical_model": canon, "estado": "activo", "candidate": False,
                        "vendido_bajo": marcas, "added_by": "s331",
                        "provenance": f"{FIRMA} — {nota}; cita verificada full-text en {d['document_family']} "
                                      f"({n} chunks con el token exacto)"},
                "doc": d["document_family"], "document_id": d["id"], "cita": txt[:220], "n_token": n,
                "regla": "alta con cita propia (anotación de Alberto verificada)"})
            docmap.append({"document_id": d["id"], "source_file": d["document_family"],
                           "entries": [{"id": pid, "role": "primary", "scope": "doc",
                                        "provenance": f"{FIRMA} — documento del propio producto ({n} chunks con el token)"}]})
        for pdf, ids, nota in DOCMAP_EXTRA:
            d = por_pdf.get(pdf)
            if d:
                docmap.append({"document_id": d["id"], "source_file": d["document_family"],
                               "entries": [{"id": i, "role": "primary", "scope": "doc",
                                            "provenance": f"{FIRMA} — {nota}"} for i in ids]})
        d = por_pdf.get(DOCMAP_STRATOS[0])
        if d:
            docmap.append({"document_id": d["id"], "source_file": d["document_family"],
                           "entries": [{"id": i, "role": "primary", "scope": "doc",
                                        "provenance": f"{FIRMA} — «modelo que propone el juez» (Alberto): NO se crea "
                                                      "producto «Stratos-HSSD»; el doc es una miniguía de FAMILIA («El "
                                                      "equipamiento puede variar según el modelo») y el paraguas STRATOS "
                                                      "ya existe (s324b) → R1 a sus 3 miembros, en simetría con MADT731_02"}
                                       for i in DOCMAP_STRATOS[1]]})
        mods = []
        for pdf, ids in (MOD_DXC, MOD_ZXDX):
            d = por_pdf.get(pdf)
            if not d:
                faltan.append({"doc": pdf, "motivo": "no activo"})
                continue
            es_dxc = "DXc" in pdf
            mods.append({
                "document_id": d["id"], "source_file": d["document_family"], "entries_nuevas": ids,
                "regla": "§1.A anotación de Alberto verificada",
                "detalle": ("QUITAR los 6 ids ZX: el PDF (1 página) trata SOLO de la DXc Connexion (MK-DXc, Windows "
                            "XP/7) y no nombra ninguna ZX. La nota «este archivo habla también de la ZX-A, ZX-E, "
                            "ZX-2/5e, ZX2/5SE» describe la FAQ HERMANA (ZX y DX), cuyo nombre es casi idéntico. Hoy "
                            "zxae/zxee tienen aquí enganchada la respuesta CONTRARIA (la ZX-A usa MS-DOS + FIRE5)")
                           if es_dxc else
                           ("AÑADIR morley:zxae y morley:zxee: el documento los nombra («Modelos de central ZX-A o "
                            "ZX-E. Programa FIRE5»). Validado a petición de Alberto: los modelos son ZXAE/ZXEE — "
                            "prueba en la tabla de equivalencias del TG «TG-ZXA | PROGRAMA GRAFICO ZXAE»; en el corpus "
                            "ZXAE 197 menciones/12 docs y ZXEE 224/13, mientras «ZX-A»/«ZX-E» salen 1 vez y solo aquí")})

    plan = {
        "que_es": ("s331 — LOTE §1.A+§1.B: las 30 anotaciones que Alberto escribió en su copia del packet E1, "
                   "verificadas una a una. Post-dúo r40."),
        "utc": "20260820T000000Z",
        "firma": "Alberto, 20-ago-2026: «Revísalo en este lote»",
        "propuesta": "evals/s331_lote_1AB_propuesta_v2.md (dúo r40)",
        "products_altas": altas, "products_confirmar": [], "products_retirar": [],
        "aliases_altas": [], "aliases_quitar": [], "umbrellas_altas": [],
        "doc_map_altas": docmap, "doc_map_modificaciones": mods, "retags_db": [],
        "no_aplicar": [
            {"tema": "retag manufacturer de ASD Harsh (Xtralis → System Sensor)",
             "estado": "FUERA por el dúo r40 (Sol, crítico): sería otro parche efímero de la clase TECH_DEBT #97 — "
                       "la reingesta re-deriva el fabricante y lo re-estampa. El dato ESTÁ mal (el doc es © 2015 "
                       "System Sensor) y afecta a `_diversify_by_manufacturer`, pero el arreglo es la AUTORIDAD DE "
                       "INGESTA, no un reaplicador hermano. Se amplía #95 a `manufacturer`"},
            {"tema": "alta avotec:doa-fj-cpd (nota «marca DOA, producto FJ/CPD»)",
             "estado": "FUERA por el dúo r40 (Sol, medio): los ids son INMUTABLES y la identidad sigue abierta — el "
                       "doc es © AVOTEC Srl y «DOA» no aparece suelta ni una vez en todo el corpus (sus 2 menciones "
                       "son «DOA FJ/CPD», una dentro de un número de certificado CE). Acuñar el id antes de que "
                       "Alberto aclare si DOA es marca sería escribir una decisión irreversible"},
            {"tema": "morley:efs-em-8 · notifier:nx2-r-r-y-nx5-r-r",
             "estado": "sin decisión de Alberto («pending.» y anotación vacía)"},
        ],
        "gaps": [
            "9-30520 es un número de parte: el precedente limpio en catálogo es UNO (spectrex:777163 activo/"
            "no-candidate) — 380114-2 y model-787640 son candidate y notifier:777163 es redirect (corregido tras "
            "Fable r40). El riesgo léxico del token numérico lo decide el gate",
            "OBJETIVO y MÉTRICA (Sol r40): esto es identidad de catálogo. El gate es el censo del radio de explosión "
            "(detector, 51 gold, negativos sintéticos, 111 consultas reales). NO mide retrieval/generación "
            "end-to-end — el writer lo reconoce explícitamente. El único efecto de serving esperado es NEGATIVO por "
            "diseño: quitar una fuente equivocada de 6 productos ZX",
            "CONV232/485 aparece como «Ref.:» (rol REFERENCIA_COMERCIAL), no como título de producto",
        ],
    }
    out = ROOT / "evals/s331_lote_1AB_plan_v1.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{out.name}: {len(altas)} altas · {len(docmap)} doc_map_altas · {len(mods)} modificaciones")
    for a in altas:
        print(f"   ALTA {a['row']['id']:24} · {a['n_token']:2} chunks · {a['cita'][:70]}")
    for m in mods:
        print(f"   MOD  {m['source_file'][:44]:46} → {len(m['entries_nuevas'])} ids")
    if faltan:
        print("FALTAN:", json.dumps(faltan, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
