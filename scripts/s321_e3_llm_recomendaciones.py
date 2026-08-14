# -*- coding: utf-8 -*-
"""s321 E3 — Pasada LLM de RECOMENDACIÓN para el residuo del packet (47 parejas).

Mandato de Alberto (13-ago, nocturno): «una pasada con el mejor modelo posible
para dejar tantos como sea posible asignados o recomendaciones con fundamento».

Diseño (dentro del marco r25 — la pasada NO auto-aplica NADA):
- Modelo: claude-fable-5 (el mejor disponible en la cuenta; el pin de la casa).
- Input por pareja: pm_prev, canónico propuesto, filename, muestra de contenido
  REAL del doc (primeros chunks), y la clase del split (producto-real/hermanas/
  no-dominante/no-atestada).
- Output estructurado: veredicto ∈ {RETAG_CANONICO, MULTI_VALOR, MANTENER_PREV,
  OTRO_PRODUCTO, NO_DECIDIBLE} + confianza ∈ {alta, media, baja} + CITA
  VERBATIM del contenido que fundamenta (sin cita → confianza baja forzada).
- Destino: TODAS van al packet como recomendación; las alta-confianza-con-cita
  quedan marcadas «aplicable en bloque si Alberto asiente» (su regla: «los que
  estés muy seguro no hace falta [que los mire]» — pero tras r24/r25, "muy
  seguro" = alta+cita+sin-hermanas, y aún así viajan listadas, no ocultas).

Coste: 47 llamadas × ~2K tokens ≈ <$2.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env", override=False)

import os  # noqa: E402

import anthropic  # noqa: E402

from src.http_pool import abierto  # noqa: E402

SB = os.environ["SUPABASE_URL"].rstrip("/")
HS = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
      "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_KEY']}"}
MODELO = "claude-fable-5"

PROMPT = """Eres el adjudicador de identidad de un corpus de manuales de protección contra incendios.

DOCUMENTO: {filename}
product_model ACTUAL de sus chunks: «{pm_prev}»
PRODUCTO CANÓNICO adjudicado en el mapa documento→producto: «{canonico}»
Clase del triage automático: {clase}

MUESTRA DEL CONTENIDO REAL del documento:
---
{muestra}
---

¿Cuál debería ser el product_model de los chunks de este documento? Responde SOLO este JSON:
{{"veredicto": "RETAG_CANONICO|MULTI_VALOR|MANTENER_PREV|OTRO_PRODUCTO|NO_DECIDIBLE",
 "multi_valor": "A/B/C si aplica, si no null",
 "otro_producto": "nombre si aplica, si no null",
 "confianza": "alta|media|baja",
 "cita": "fragmento VERBATIM del contenido que fundamenta (o null)",
 "razon": "una frase"}}

Reglas: RETAG_CANONICO solo si el contenido muestra que el doc trata ESE producto como sujeto. MULTI_VALOR si el doc cubre varias variantes/productos con contenido propio (convención lista-con-barras). MANTENER_PREV si el pm actual es el correcto. Sin cita verbatim → tu confianza es baja."""


def main() -> int:
    atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                       .read_text(encoding="utf-8"))
    residuo = [dict(f, clase=k) for k in ("pm_prev_producto_real",
                                          "ambigua_hermanas", "no_dominante",
                                          "no_atestada")
               for f in atest["detalle"][k]]
    cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                                  timeout=120.0, max_retries=1)
    filas = []
    with abierto(timeout=30.0) as c:
        for i, f in enumerate(residuo):
            r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                      params={"select": "content",
                              "document_id": f"eq.{f['document_id']}",
                              "product_model": f"eq.{f['pm_prev']}",
                              "order": "chunk_index.asc", "limit": "4"})
            r.raise_for_status()
            muestra = "\n...\n".join((x.get("content") or "")[:1200]
                                     for x in r.json())
            # sin temperature: deprecada en los modelos 2026 (clase DEC-092)
            msg = cliente.messages.create(
                model=MODELO, max_tokens=400,
                messages=[{"role": "user", "content": PROMPT.format(
                    filename=f["source_file"], pm_prev=f["pm_prev"],
                    canonico=f["canonico"], clase=f["clase"],
                    muestra=muestra[:6000])}])
            texto = "".join(b.text for b in msg.content
                            if getattr(b, "type", "") == "text").strip()
            try:
                inicio = texto.index("{")
                fin = texto.rindex("}") + 1
                veredicto = json.loads(texto[inicio:fin])
            except Exception:                     # noqa: BLE001
                veredicto = {"veredicto": "NO_DECIDIBLE", "confianza": "baja",
                             "cita": None, "razon": "parse-fail",
                             "raw": texto[:300]}
            cita_ok = bool(veredicto.get("cita")) and (
                veredicto["cita"][:60].lower() in muestra.lower())
            if veredicto.get("confianza") == "alta" and not cita_ok:
                veredicto["confianza"] = "media"
                veredicto["nota"] = "cita no verificada en muestra → degradada"
            filas.append({**{k: f[k] for k in ("document_id", "source_file",
                                               "pm_prev", "canonico", "chunks",
                                               "clase")},
                          "llm": veredicto, "cita_verificada": cita_ok})
            print(f"  {i+1}/{len(residuo)} {f['pm_prev']!r}: "
                  f"{veredicto.get('veredicto')} ({veredicto.get('confianza')})",
                  flush=True)
            time.sleep(0.3)

    utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    resumen = {}
    for fila in filas:
        k = (fila["llm"].get("veredicto"), fila["llm"].get("confianza"))
        resumen[f"{k[0]}:{k[1]}"] = resumen.get(f"{k[0]}:{k[1]}", 0) + 1
    recibo = {
        "que_es": ("Recomendaciones LLM (claude-fable-5) para el residuo E3. "
                   "NADA auto-aplicado: alta+cita-verificada = «aplicable en "
                   "bloque si Alberto asiente»; el resto, recomendación."),
        "utc": utc, "modelo": MODELO, "total": len(filas),
        "resumen": resumen, "detalle": filas,
    }
    destino = ROOT / "evals" / "s321_e3_llm_recomendaciones_v1.json"
    destino.write_text(json.dumps(recibo, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    print(f"total {len(filas)} · resumen {resumen}")
    print(f"recibo -> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
