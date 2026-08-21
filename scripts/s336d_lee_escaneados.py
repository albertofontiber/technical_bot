#!/usr/bin/env python
"""s336d — leer con Claude los huérfanos que NINGÚN otro camino alcanza.

De los 84 huérfanos, el diagnóstico s336c dejó 3 fuera de todo camino de texto:
dos PDF escaneados (capa de texto vacía: 0,0 chars/página) y uno sin PDF en
Storage. Los tres son `unresolved:` — o sea que su promoción pasa por la
adjudicación de Alberto (R21) igualmente. Esto NO los promueve: les pone
evidencia delante, para que la adjudicación no sea a ciegas.

Lector: **Anthropic** (preferencia de Alberto, s336e). Gemini queda como
alternativa explícita, no como opción por defecto.

Guardarraíl anti-fuga: al modelo NO se le dice qué espera el catálogo ni cómo se
llama el fichero — si el token esperado o el nombre del fichero aparecen en el
payload, aborta. Sin eso, «lo ha visto» sólo probaría que sabe leer mi prompt.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY      # noqa: E402

SB = SUPABASE_URL.rstrip("/") + "/rest/v1"
H = {"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"}
DIAG = ROOT / "evals/s336c_diagnostico_huerfanos.json"
SALIDA = ROOT / "evals/s336d_lectura_escaneados.json"
MODELO = os.environ.get("MODELO_VISION", "claude-fable-5")
#: 150 DPI: un escaneo de manual se lee de sobra y la imagen no se dispara de tamaño.
DPI = 150

PROMPT = ("Esta es una página de un manual técnico de protección contra incendios. "
          "Dime QUÉ MODELOS DE PRODUCTO se nombran en ella, copiando la grafía exacta "
          "que aparece impresa. Si la página no nombra ningún modelo concreto, "
          "devuelve la lista vacía — no adivines a partir del tipo de producto. "
          'Responde SOLO JSON: {"modelos": ["..."], "texto_visible": "los primeros '
          '200 caracteres que leas", "confianza": "alta|media|baja"}')


class Fuga(RuntimeError):
    """El payload contenía la respuesta. El resultado no valdría nada."""


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def sin_fuga(payload: object, esperado: str, fichero: str) -> None:
    crudo = json.dumps(payload, ensure_ascii=False)
    crudo = re.sub(r'"data"\s*:\s*"[^"]*"', '"data":"<img>"', crudo)
    n = _norm(crudo)
    for etiqueta, valor in (("token esperado", esperado), ("nombre del fichero", fichero)):
        v = _norm(valor)
        if v and len(v) >= 4 and v in n:
            raise Fuga(f"el payload contiene el {etiqueta} («{valor}»)")


def _autotest() -> None:
    """Un guardarraíl que no se prueba a sí mismo es decorado."""
    try:
        sin_fuga({"m": [{"text": "identifica el SCD-120 de la pagina"}]}, "SCD-120", "x")
    except Fuga:
        return
    raise SystemExit("el guardarraíl anti-fuga NO salta con un payload envenenado")


def _json_de(t: str) -> dict:
    m = re.search(r"\{.*\}", t or "", re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:                                       # noqa: BLE001
            pass
    return {"modelos": [], "confianza": "baja", "_crudo": (t or "")[:300]}


def lee(img: bytes, mime: str, esperado: str, fichero: str) -> dict:
    payload = {"model": MODELO, "max_tokens": 700, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": mime,
                                     "data": base64.b64encode(img).decode()}},
        {"type": "text", "text": PROMPT}]}]}
    sin_fuga(payload, esperado, fichero)
    r = httpx.post("https://api.anthropic.com/v1/messages",
                   headers={"x-api-key": os.environ["ANTHROPIC_API_KEY_SCRIPTS"],
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json"},
                   json=payload, timeout=240)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:200]}")
    d = r.json()
    return _json_de("".join(b.get("text", "") for b in d.get("content", [])))


def paginas_del_pdf(url: str) -> list[tuple[bytes, str]]:
    with httpx.Client(timeout=300, follow_redirects=True) as c:
        r = c.get(url)
        r.raise_for_status()
    doc = fitz.open(stream=r.content, filetype="pdf")
    out = []
    for p in doc:
        pix = p.get_pixmap(dpi=DPI)
        out.append((pix.tobytes("jpeg" if hasattr(pix, "tobytes") else "png"), "image/jpeg"))
    doc.close()
    return out


def paginas_guardadas(document_id: str) -> list[tuple[bytes, str]]:
    with httpx.Client(timeout=180) as c:
        r = c.get(f"{SB}/document_visual_assets", headers=H,
                  params={"select": "page_index,storage_url", "document_id": f"eq.{document_id}",
                          "order": "page_index"})
        r.raise_for_status()
        out = []
        for a in r.json():
            im = c.get(a["storage_url"], timeout=120)
            im.raise_for_status()
            out.append((im.content, im.headers.get("content-type", "image/jpeg").split(";")[0]))
    return out


def main() -> int:
    _autotest()
    print(f"guardarraíl anti-fuga: AUTO-TEST OK · lector = {MODELO} (Anthropic)\n")
    diag = json.loads(DIAG.read_text("utf-8"))
    objetivo = [f for f in diag["filas"] if f["bucket"] in ("LECTOR_MULTIMODAL", "SIN_PDF")]
    docs = {}
    with httpx.Client(timeout=120) as c:
        r = c.get(f"{SB}/documents", headers=H, params={"select": "id,source_url"})
        r.raise_for_status()
        docs = {str(x["id"]): str(x.get("source_url") or "") for x in r.json()}

    filas = []
    for f in objetivo:
        esperado = (f["canonicos"] or [""])[0]
        url = docs.get(f["document_id"], "")
        print(f"── {f['source_file'][:52]}  ({f['bucket']})")
        try:
            pgs = (paginas_del_pdf(url) if f["bucket"] == "LECTOR_MULTIMODAL" and url
                   else paginas_guardadas(f["document_id"]))
        except Exception as e:                                  # noqa: BLE001
            print(f"     no se pudo obtener la imagen: {str(e)[:120]}")
            filas.append({**f, "lectura": [], "error": str(e)[:160]})
            continue
        lect = []
        for i, (img, mime) in enumerate(pgs, 1):
            try:
                d = lee(img, mime, esperado, f["source_file"])
            except Fuga:
                raise
            except Exception as e:                              # noqa: BLE001
                d = {"error": str(e)[:160]}
            lect.append(d)
            vis = (d.get("texto_visible") or d.get("error") or "")[:74]
            print(f"     pág {i}/{len(pgs)}  modelos={d.get('modelos', [])}  «{vis}»")
        # ¿coincide con lo que el catálogo dice que es? SOLO se comprueba DESPUÉS.
        leidos = {_norm(x) for d in lect for x in d.get("modelos", [])}
        coincide = _norm(esperado) in leidos if esperado else False
        print(f"     → el catálogo dice «{esperado}» · el lector "
              f"{'LO CONFIRMA' if coincide else 'NO lo nombra'}")
        filas.append({**f, "lectura": lect, "coincide_con_catalogo": coincide})

    SALIDA.write_text(json.dumps(
        {"que_es": "s336d · lectura con Anthropic de los 3 huérfanos sin camino de texto "
                   "(2 PDF escaneados + 1 sin PDF). NO promueve nada: los tres son "
                   "`unresolved:` y su promoción pasa por la adjudicación R21 de Alberto. "
                   "Esto es evidencia PARA esa adjudicación.",
         "modelo": MODELO, "dpi": DPI, "n": len(filas), "filas": filas},
        ensure_ascii=False, indent=1), "utf-8")
    print(f"\n→ {SALIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
