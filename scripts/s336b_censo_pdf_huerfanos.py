#!/usr/bin/env python
"""s336b — ¿por qué está huérfano cada manual? Censo sobre el PDF ORIGINAL.

Contexto. La sonda multimodal (s336) leía las páginas guardadas en
`document_visual_assets`, que son una SELECCIÓN (mediana: 2 páginas por
huérfano, de manuales de 30). Sus negativos no eran del modelo: eran de la
cobertura. Y mirando dos de esas páginas a mano se ve que los lectores
acertaban — en la portada del FAD-902 pone «GUIDE MANUAL / Power Supplies» y
el modelo NO aparece; el nombre vive en el cuerpo, que es justo lo que dice R9.

Los PDF originales SÍ están en Storage (`documents.source_url`, 83 de los 84).
Así que la pregunta cara —¿qué modelo lee mejor la página?— viene DESPUÉS de
una gratis: **¿está el nombre en la capa de texto del PDF?** Si está, no hace
falta ningún lector multimodal: lo perdimos nosotros al extraer, y el arreglo
es de raíz (re-extracción), no de modelo.

Tres veredictos, y cada uno manda a una herramienta distinta:
  · EN_TEXTO_PDF — el nombre está en el PDF y no llegó a `chunks`. Fallo NUESTRO.
  · PDF_SIN_TEXTO — el PDF es escaneado (sin capa de texto útil): ahí, y sólo
    ahí, un lector multimodal / OCR es la herramienta correcta.
  · NO_ESTA_EN_EL_PDF — el PDF tiene texto bueno y aun así no lo nombra: el
    manual de verdad no atesta ese producto (R14/R9), y ningún modelo lo cambia.

NADA se aplica: esto es un censo. Escribe recibo y sale.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402
from src.rag import catalog_store as cs                        # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
SALIDA = ROOT / "evals/s336b_censo_pdf_huerfanos.json"
#: Umbral de «capa de texto útil». Un PDF escaneado devuelve casi nada por
#: página; uno digital, cientos de caracteres. 40 deja margen a portadas sueltas.
MIN_CHARS_POR_PAGINA = 40


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _patron(token: str) -> str | None:
    """El separador NO es estable: el mismo modelo se escribe `AM-6000` y
    `AM6000`, `TG-IP-1-SEC` y `TG-IP1-SEC`. Así que el token se parte en tramos
    —por separador Y por el salto letra↔dígito— y entre tramos se admite UN
    separador opcional. Los extremos siguen pidiendo frontera, que es lo que
    impide que `2001` case dentro de `12001` o `AFP400` dentro de `AFP400X`."""
    t = _norm(token)
    if not t:
        return None
    tramos = [x for x in re.findall(r"[a-z]+|[0-9]+", t) if x]
    if not tramos:
        return None
    return (r"(?<![a-z0-9])" + r"[^a-z0-9]?".join(re.escape(x) for x in tramos)
            + r"(?![a-z0-9])")


def cita(texto: str, token: str) -> bool:
    """¿El texto NOMBRA el token? Frontera en los extremos, separador flexible
    dentro. `MAD-491` casa con «MAD 491» y «MAD491»; `2001` NO casa en «12001»."""
    pat = _patron(token)
    return bool(pat) and re.search(pat, _norm(texto)) is not None


def pagina(tabla: str, params: dict, orden: str = "id") -> list[dict]:
    """Paginar SIN `order` es un BUG: PostgREST no garantiza orden estable entre
    rangos, así que la paginación salta y duplica filas. Lo cacé porque dos pases
    idénticos de la huella de detección dieron `AM-LCD=2` y `AM-LCD=6`, y porque
    el corpus salía con 954 documentos cuando tiene 1.080. Con `order` explícito
    es determinista, y se comprueba contra el total de `count=exact` en vez de
    confiar en que la última página vino corta."""
    out, desde = [], 0
    with httpx.Client(timeout=180) as c:
        r0 = c.get(f"{SB}/{tabla}", headers={**H, "Prefer": "count=exact"},
                   params={**params, "limit": "1"})
        total = int((r0.headers.get("content-range") or "0/0").split("/")[-1] or 0)
        while True:
            r = c.get(f"{SB}/{tabla}", headers={**H, "Range-Unit": "items",
                      "Range": f"{desde}-{desde+999}"},
                      params={**params, "order": orden})
            r.raise_for_status()
            d = r.json()
            out += d
            if len(d) < 1000:
                break
            desde += 1000
    if len(out) != total:
        raise SystemExit(f"paginación incompleta en {tabla}: {len(out)} de {total}")
    return out


def huerfanos() -> list[dict]:
    """Huérfano = ningún id de su `doc_map` es consumible. Se usa el predicado
    del PROPIO resolver (`_consumable`, que sigue redirects a propósito): la
    definición ingenua contaba 59 manuales que nunca lo fueron."""
    cat = cs.load()
    por_id: dict[str, list[str]] = {}
    for a in cat.aliases:
        por_id.setdefault(str(a.get("id", "")), []).append(str(a.get("alias", "")))
    out = []
    for f in cat.doc_map:
        ids = [e["id"] for e in f.get("entries", []) if e["id"] in cat.products]
        if not ids or any(cat._consumable(i) for i in ids):
            continue
        # Los nombres que el manual DEBERÍA citar: canónico + alias de cada id.
        tokens: list[str] = []
        for i in ids:
            p = cat.products[i]
            tokens.append(p.get("canonical_model", ""))
            tokens += por_id.get(i, [])
        out.append({"document_id": str(f.get("document_id") or ""),
                    "source_file": str(f.get("source_file") or ""),
                    "ids": ids, "tokens": sorted({t for t in tokens if t})})
    return out


def main() -> int:
    hu = huerfanos()
    docs = {str(d["id"]): d for d in
            pagina("documents", {"select": "id,source_url,source_pdf_filename"})}
    print(f"=== CENSO SOBRE EL PDF ORIGINAL · {len(hu)} huérfanos ===\n")

    filas, cuenta = [], Counter()
    with httpx.Client(timeout=300, follow_redirects=True) as c:
        for i, h in enumerate(hu, 1):
            d = docs.get(h["document_id"], {})
            url = str(d.get("source_url") or "")
            fila = {**h, "source_url_ok": url.startswith(("http://", "https://"))}
            if not fila["source_url_ok"]:
                fila["veredicto"] = "SIN_PDF"
            else:
                try:
                    r = c.get(url)
                    r.raise_for_status()
                    doc = fitz.open(stream=r.content, filetype="pdf")
                    textos = [p.get_text() for p in doc]
                    n_pag = len(textos)
                    chars = sum(len(t) for t in textos)
                    todo = "\n".join(textos)
                    hits = [t for t in h["tokens"] if cita(todo, t)]
                    # ¿en qué páginas? sirve para saber si la selección guardada
                    # podía haberlo visto siquiera
                    paginas_hit = sorted({j + 1 for j, t in enumerate(textos)
                                          for tk in hits if cita(t, tk)})
                    fila.update({"n_paginas_pdf": n_pag,
                                 "chars_por_pagina": round(chars / max(n_pag, 1), 1),
                                 "tokens_citados": hits[:8],
                                 "paginas_donde_cita": paginas_hit[:12]})
                    if hits:
                        fila["veredicto"] = "EN_TEXTO_PDF"
                    elif chars / max(n_pag, 1) < MIN_CHARS_POR_PAGINA:
                        fila["veredicto"] = "PDF_SIN_TEXTO"
                    else:
                        fila["veredicto"] = "NO_ESTA_EN_EL_PDF"
                    doc.close()
                except Exception as e:                          # noqa: BLE001
                    fila["veredicto"] = "LECTURA_FALLIDA"
                    fila["error"] = str(e)[:160]
            cuenta[fila["veredicto"]] += 1
            filas.append(fila)
            print(f"  [{i:2d}/{len(hu)}] {h['source_file'][:40]:42s} {fila['veredicto']}"
                  + (f"  ← {', '.join(fila.get('tokens_citados', [])[:3])}"
                     f" (pág. {fila.get('paginas_donde_cita', [])[:4]})"
                     if fila["veredicto"] == "EN_TEXTO_PDF" else ""))

    print(f"\n=== VEREDICTOS ===")
    for k, v in cuenta.most_common():
        print(f"  {k:20s} {v:3d}")
    print("\n  EN_TEXTO_PDF     → el nombre ESTÁ y lo perdimos al extraer: arreglo de raíz")
    print("  PDF_SIN_TEXTO    → escaneado: aquí sí manda un lector multimodal / OCR")
    print("  NO_ESTA_EN_EL_PDF→ el manual no atesta ese producto: ningún modelo lo cambia")

    SALIDA.write_text(json.dumps(
        {"que_es": "s336b · censo sobre el PDF original de cada manual huérfano. "
                   "Separa lo que perdimos al extraer de lo que de verdad no está. "
                   "NADA aplicado.",
         "umbral_chars_por_pagina": MIN_CHARS_POR_PAGINA,
         "n": len(filas), "veredictos": dict(cuenta), "filas": filas},
        ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
