# -*- coding: utf-8 -*-
"""s315 (punto 6): backfill de `documents.source_url` desde manifiestos de harvest.

Fuente v1 = el manifiesto Casmar s314 (`evals/s314_casmar_batch_report_v1.json`:
url + sha256 por PDF). El join es por `documents.source_pdf_sha256` — la identidad
de CONTENIDO, no el nombre de fichero (los dups del PIM comparten sha con URL
distinta: se toma la primera URL por sha, determinista por orden del manifiesto).

Gap declarado: los documentos históricos (OneDrive, scrapes antiguos sin manifiesto
sha) quedan con source_url NULL → la leyenda no emite link para ellos. Ampliar el
backfill = añadir manifiestos con (url, sha256), no tocar este join.

Modos:
  (default)   dry-run: imprime el plan y el recibo, no toca la DB.
  --aplicar   ejecuta los UPDATE vía PostgREST (requiere SUPABASE_URL/SERVICE_KEY).
  --sql-out F escribe los UPDATE como SQL a F (para aplicar vía SQL Editor/MCP).
Recibo JSON (siempre): evals/s315_source_url_backfill_v1.json — con él el patch
inverso es `set source_url = null where id in (...)`.
"""
import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFIESTO = os.path.join(REPO, "evals", "s314_casmar_batch_report_v1.json")
RECIBO = os.path.join(REPO, "evals", "s315_source_url_backfill_v1.json")


def urls_por_sha() -> dict[str, str]:
    filas = json.load(open(MANIFIESTO, encoding="utf-8"))
    out: dict[str, str] = {}
    for fila in filas:
        sha, url = fila.get("sha256"), fila.get("url")
        if sha and url and sha not in out:
            out[sha] = url
    return out


def docs_con_sha(client) -> list[dict]:
    """Filas de documents con sha real (los placeholders 'backfill:' no casan)."""
    resp = client.get(
        "/rest/v1/documents",
        params={"select": "id,source_pdf_sha256,source_pdf_filename,source_url",
                "source_pdf_sha256": "not.is.null", "limit": "10000"},
    )
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--sql-out")
    args = ap.parse_args()

    mapa = urls_por_sha()
    import httpx

    sys.path.insert(0, REPO)
    from src.config import SUPABASE_SERVICE_KEY, SUPABASE_URL

    headers = {"apikey": SUPABASE_SERVICE_KEY,
               "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
    with httpx.Client(base_url=SUPABASE_URL, headers=headers, timeout=30) as client:
        docs = docs_con_sha(client)
        plan = [
            {"id": d["id"], "doc": d.get("source_pdf_filename"),
             "url": mapa[d["source_pdf_sha256"]]}
            for d in docs
            if d.get("source_pdf_sha256") in mapa and not d.get("source_url")
        ]
        ya = sum(1 for d in docs if d.get("source_url"))
        print(f"manifiesto: {len(mapa)} sha con URL · documents con sha: {len(docs)} "
              f"· a poblar: {len(plan)} · ya pobladas: {ya}")

        recibo = {"motivo": "s315 punto 6: URL pública para la leyenda de fuentes",
                  "fuente": os.path.basename(MANIFIESTO),
                  "reversible": "UPDATE documents SET source_url=NULL WHERE id IN (ids del recibo)",
                  "cambios": plan}
        json.dump(recibo, open(RECIBO, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"recibo -> {RECIBO}")

        if args.sql_out:
            with open(args.sql_out, "w", encoding="utf-8") as fh:
                for c in plan:
                    url = c["url"].replace("'", "''")
                    fh.write("update public.documents set source_url = "
                             f"'{url}' where id = '{c['id']}' "
                             "and source_url is null;\n")
            print(f"sql -> {args.sql_out}")
        if not args.aplicar:
            print("(dry-run; --aplicar para ejecutar)")
            return 0

        aplicadas = 0
        for c in plan:
            resp = client.patch(
                "/rest/v1/documents",
                params={"id": f"eq.{c['id']}", "source_url": "is.null"},
                json={"source_url": c["url"]},
                headers={"Prefer": "return=minimal"},
            )
            resp.raise_for_status()
            aplicadas += 1
        print(f"APLICADAS: {aplicadas}/{len(plan)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
