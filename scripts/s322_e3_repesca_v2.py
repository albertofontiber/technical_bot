# -*- coding: utf-8 -*-
"""s322c — REPESCA v2 del residuo E3 (las 32 filas §1 del packet).

Pregunta de Alberto (14-ago): «¿no habíamos dicho de revisar las de confianza
no-alta online para aumentar la confianza?» — orden probado en #76: CORPUS
PRIMERO, online solo para el residuo irreducible.

Diagnóstico de las 32: 12 son `parse-fail` (la pasada v1 usó max_tokens=400 —
el MISMO bug de truncado cazado en la población #76) y ~17 ya están en alta
con cita ✓ pero cayeron a §1 solo por HERMANAS presentes. Fixes v2:
- max_tokens 400→800 (la causa raíz de los parse-fail);
- muestreo del doc ENTERO (sin filtrar por pm_prev) + chunks que mencionan el
  canónico (la fila de la tabla/portada suele vivir fuera de la ventana);
- verificación de citas FULL-TEXT contra el doc completo (estándar r28);
- salida nueva `hermanas_sujeto` ∈ {unico, multi} con SU cita: convierte la
  pregunta multi-valor en criterio de máquina (§0-bis = alta + cita ✓ +
  hermanas_sujeto=unico con cita verificada) en vez de prosa.

NADA se aplica: el recibo v2 alimenta el packet v2 para la sentada de Alberto.
El recibo v1 no se muta (recibos inmutables).
"""
from __future__ import annotations

import json
import re
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
Variantes HERMANAS detectadas en el contenido: {hermanas}

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
 "hermanas_sujeto": "unico|multi|null — si hay hermanas: ¿el doc trata UN sujeto (las hermanas son accesorios/referencias) o VARIAS con contenido propio?",
 "hermanas_cita": "fragmento VERBATIM que fundamenta hermanas_sujeto (o null)",
 "razon": "una frase"}}

Reglas: RETAG_CANONICO solo si el contenido muestra que el doc trata ESE producto como sujeto. MULTI_VALOR si el doc cubre varias variantes/productos con contenido propio (convención lista-con-barras). MANTENER_PREV si el pm actual es el correcto. Sin cita verbatim → tu confianza es baja. Si hay hermanas, `hermanas_sujeto` es OBLIGATORIO y su cita debe mostrar el papel de las hermanas (p.ej. la frase donde son solo accesorio de montaje)."""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


atest = json.loads((ROOT / "evals" / "s321_e3_atestacion_v1.json")
                   .read_text(encoding="utf-8"))
v1 = json.loads((ROOT / "evals" / "s321_e3_llm_recomendaciones_v1.json")
                .read_text(encoding="utf-8"))
atest_por_clave = {(f["document_id"], f["pm_prev"]): dict(f, clase=k)
                   for k in ("pm_prev_producto_real", "ambigua_hermanas",
                             "no_dominante", "no_atestada")
                   for f in atest["detalle"][k]}

# objetivo = las filas que NO cumplen el criterio §0 v1 (las 32 del packet)
objetivo = []
for fila in v1["detalle"]:
    a = atest_por_clave.get((fila["document_id"], fila["pm_prev"]), {})
    en_s0 = (fila["llm"].get("confianza") == "alta"
             and fila.get("cita_verificada") and not a.get("hermanas"))
    if not en_s0:
        objetivo.append(fila)
print(f"objetivo v2: {len(objetivo)} filas")

doc_cache: dict[str, str] = {}


def _doc_completo(client, document_id: str) -> str:
    if document_id not in doc_cache:
        trozos, offset = [], 0
        while True:
            r = client.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                           params={"select": "content",
                                   "document_id": f"eq.{document_id}",
                                   "order": "chunk_index.asc",
                                   "offset": str(offset), "limit": "100"})
            r.raise_for_status()
            lote = r.json()
            trozos.extend((x.get("content") or "") for x in lote)
            if len(lote) < 100:
                break
            offset += 100
        doc_cache[document_id] = "\n".join(trozos)
    return doc_cache[document_id]


cliente = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"],
                              timeout=120.0, max_retries=1)
v2_filas, resumen = [], {}
with abierto(timeout=30.0) as c:
    for i, fila in enumerate(objetivo):
        a = atest_por_clave[(fila["document_id"], fila["pm_prev"])]
        did = fila["document_id"]
        # muestreo v2: doc entero (primeros 5) + chunks que mencionan el canónico
        r = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                  params={"select": "content", "document_id": f"eq.{did}",
                          "order": "chunk_index.asc", "limit": "5"})
        r.raise_for_status()
        trozos = [(x.get("content") or "")[:1600] for x in r.json()]
        rv = c.get(f"{SB}/rest/v1/chunks_v2", headers=HS,
                   params={"select": "content", "document_id": f"eq.{did}",
                           "content": f"ilike.*{fila['canonico']}*",
                           "order": "chunk_index.asc", "limit": "3"})
        if rv.status_code == 200:
            trozos += [f"[menciona {fila['canonico']}]\n" + (x.get("content") or "")[:1600]
                       for x in rv.json()]
        muestra = "\n...\n".join(trozos)[:12000]
        msg = cliente.messages.create(
            model=MODELO, max_tokens=800,   # v1 usaba 400: causa de los parse-fail
            messages=[{"role": "user", "content": PROMPT.format(
                filename=fila["source_file"], pm_prev=fila["pm_prev"],
                canonico=fila["canonico"], clase=fila["clase"],
                hermanas=list(a.get("hermanas") or {}) or "ninguna",
                muestra=muestra)}])
        texto = "".join(b.text for b in msg.content
                        if getattr(b, "type", "") == "text").strip()
        try:
            v = json.loads(texto[texto.index("{"):texto.rindex("}") + 1])
        except Exception:                     # noqa: BLE001
            v = {"veredicto": "NO_DECIDIBLE", "confianza": "baja",
                 "cita": None, "razon": "parse-fail v2", "raw": texto[:300]}
        doc_norm = _norm(_doc_completo(c, did))

        def _ok(cita):
            frag = _norm((cita or "")[:200])
            return bool(frag) and frag in doc_norm

        cita_ok = _ok(v.get("cita"))
        hermanas_ok = (not a.get("hermanas")) or (
            v.get("hermanas_sujeto") == "unico" and _ok(v.get("hermanas_cita")))
        if v.get("confianza") == "alta" and not cita_ok:
            v["confianza"] = "media"
            v["nota"] = "cita no verificada full-text → degradada"
        nueva = {**{k: fila[k] for k in ("document_id", "source_file", "pm_prev",
                                        "canonico", "chunks", "clase")},
                 "llm": v, "cita_verificada": cita_ok,
                 "hermanas_resueltas": hermanas_ok,
                 "repesca": "v2 s322c (800 tokens, doc entero, full-text)"}
        v2_filas.append(nueva)
        k = f"{v.get('veredicto')}:{v.get('confianza')}"
        resumen[k] = resumen.get(k, 0) + 1
        print(f"  {i+1}/{len(objetivo)} {fila['pm_prev']!r}: "
              f"{v.get('veredicto')} ({v.get('confianza')}"
              f"{', cita ✓' if cita_ok else ''}"
              f"{', hermanas ✓' if a.get('hermanas') and hermanas_ok else ''})",
              flush=True)
        time.sleep(0.3)

# recibo v2 = v1 con las filas re-corridas SUSTITUIDAS (v1 queda intacto)
por_clave_v2 = {(f["document_id"], f["pm_prev"]): f for f in v2_filas}
detalle = [por_clave_v2.get((f["document_id"], f["pm_prev"]), f)
           for f in v1["detalle"]]
utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(ROOT / "evals" / "s321_e3_llm_recomendaciones_v2.json").write_text(
    json.dumps({"que_es": ("Repesca v2 s322c del residuo E3 (32 filas §1): "
                           "max_tokens 800, muestreo doc-entero+canónico, "
                           "verificación full-text, hermanas_sujeto con cita. "
                           "NADA aplicado — alimenta el packet v2."),
                "utc": utc, "modelo": MODELO, "base": "v1 + repesca",
                "resumen_repesca": resumen, "detalle": detalle},
               ensure_ascii=False, indent=1), encoding="utf-8")
print(f"repesca v2: {len(v2_filas)} filas · resumen {resumen}")
