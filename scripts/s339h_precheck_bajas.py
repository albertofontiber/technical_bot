#!/usr/bin/env python3
"""s339h — antes de borrar un documento del corpus, comprobar qué se lleva por delante.

Alberto firmó cuatro bajas («elimínalo del corpus», «retira este manual», «es portugués,
deberíamos sacarlo»). Borrar es irreversible y el daño no se ve en el fichero que se borra
sino en lo que dependía de él, así que esto lo mide ANTES:

  · **golds** — ¿alguna respuesta de oro se apoya en este documento, y es el ÚNICO que la
    sostiene? Un gold que se queda sin portador es una regresión silenciosa del eval.
  · **doc_map** — ¿qué productos se quedan sin ninguna fuente al perderlo? Un producto
    consumible sin documentos vuelve a ser inalcanzable.
  · **gemelo** — para las bajas por idioma, ¿existe de verdad la versión que se conserva?

No borra nada. Sólo dice qué costaría.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

import httpx  # noqa: E402
import yaml   # noqa: E402

from src.rag import catalog_store as cs  # noqa: E402

U, K = os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}
TABLA = os.environ.get("CHUNKS_TABLE", "chunks_v2")
SALIDA = RAIZ / "evals" / "s339h_precheck_bajas.json"

# Las cuatro bajas firmadas, con la frase de Alberto que las autoriza.
BAJAS = [
    ("MNDT740P", "«el manual MNDT740P es portugués, así que deberíamos sacarlo»", "MNDT741"),
    ("MNDT741I", "«si los documentos 2 y 3 son iguales, y solo cambia el idioma, quitaría "
                 "el de MNDT741I»", "MNDT741"),
    ("S3466R_Eng_ital", "«retira este manual del corpus»", None),
    # OJO: el manual de `unresolved:indicator` es `Indicator Honeywell Manual SP`, NO
    # `MIEMA130` — ése es el de `unresolved:vision-plus`, que el lote PROMUEVE. Esta lista
    # llegó a tener el fichero equivocado y lo cazó este mismo precheck: habría borrado el
    # manual de la VSN Plus mientras el lote la daba de alta.
    ("Indicator Honeywell Manual SP", "«Elimínalo del corpus» (§7 `unresolved:indicator`)", None),
]


def main() -> int:
    cat = cs.load()
    golds = yaml.safe_load((RAIZ / "evals/gold_answers_v1.yaml").read_text("utf-8"))

    with httpx.Client(base_url=U, headers=H, timeout=120) as c:
        docs = []
        off = 0
        while True:
            r = c.get("/rest/v1/documents", headers={**H, "Range-Unit": "items",
                      "Range": f"{off}-{off + 999}"},
                      params={"select": "id,source_pdf_filename,language,status", "order": "id"})
            r.raise_for_status()
            j = r.json()
            docs += j
            if len(j) < 1000:
                break
            off += 1000
        por_nombre = {str(d.get("source_pdf_filename") or ""): d for d in docs}

        filas = []
        for nombre, cita, gemelo in BAJAS:
            cand = [v for k, v in por_nombre.items() if k.startswith(nombre)]
            if not cand:
                filas.append({"manual": nombre, "cita": cita, "estado": "NO ESTÁ EN documents",
                              "riesgo": "ninguno — nada que borrar"})
                continue
            d = cand[0]
            did = d["id"]
            rc = c.get(f"/rest/v1/{TABLA}", headers={**H, "Prefer": "count=exact"},
                       params={"document_id": f"eq.{did}", "select": "id", "limit": "1"})
            n_chunks = int((rc.headers.get("content-range") or "0/0").split("/")[-1] or 0)

            # ¿Qué productos pierden fuente? Y de esos, ¿cuáles se quedan a cero?
            entrada = next((m for m in cat.doc_map if str(m.get("document_id")) == did), None)
            ids = [str(e["id"]) for e in (entrada or {}).get("entries", [])]
            se_quedan_sin_fuente = []
            for pid in ids:
                otras = [m for m in cat.doc_map
                         if str(m.get("document_id")) != did
                         and any(str(e["id"]) == pid for e in m.get("entries", []))]
                if not otras:
                    se_quedan_sin_fuente.append(pid)

            # ¿Algún gold lo cita como fuente esperada?
            tocados = [g for g in golds
                       if nombre.lower() in json.dumps(g, ensure_ascii=False).lower()]

            estado_gemelo = None
            if gemelo:
                g = [k for k in por_nombre if k.startswith(gemelo) and not k.startswith(nombre)]
                estado_gemelo = {"busca": gemelo, "encontrados": g,
                                 "language": [por_nombre[x].get("language") for x in g]}

            riesgo = "bajo"
            if tocados:
                riesgo = "ALTO — hay gold que lo menciona"
            elif se_quedan_sin_fuente:
                riesgo = f"MEDIO — {len(se_quedan_sin_fuente)} producto(s) se quedan sin fuente"
            elif gemelo and not (estado_gemelo or {}).get("encontrados"):
                riesgo = "ALTO — la versión que se conserva NO existe"

            filas.append({"manual": d["source_pdf_filename"], "document_id": did,
                          "cita": cita, "language": d.get("language"), "status": d.get("status"),
                          "chunks": n_chunks, "productos_del_doc_map": ids,
                          "se_quedan_sin_fuente": se_quedan_sin_fuente,
                          "golds_que_lo_mencionan": len(tocados),
                          "gemelo": estado_gemelo, "riesgo": riesgo})

    SALIDA.write_text(json.dumps({"bajas": filas}, ensure_ascii=False, indent=1), "utf-8")
    for f in filas:
        print("\n── " + str(f["manual"]))
        if f.get("estado"):
            print("   " + f["estado"])
        else:
            print("   chunks=%s lang=%s status=%s"
                  % (f.get("chunks"), f.get("language"), f.get("status")))
        if f.get("productos_del_doc_map") is not None:
            print(f"   productos del doc_map : {f['productos_del_doc_map'] or '—'}")
            print(f"   se quedan SIN fuente  : {f['se_quedan_sin_fuente'] or 'ninguno'}")
            print(f"   golds que lo mencionan: {f['golds_que_lo_mencionan']}")
            if f.get("gemelo"):
                print(f"   gemelo que se conserva: {f['gemelo']['encontrados']} "
                      f"lang={f['gemelo']['language']}")
        print(f"   RIESGO: {f['riesgo']}")
    altos = [f for f in filas if f["riesgo"].startswith("ALTO")]
    print(f"\n{len(altos)} baja(s) en riesgo ALTO")
    print(f"→ {SALIDA.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
