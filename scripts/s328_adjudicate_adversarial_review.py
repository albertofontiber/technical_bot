#!/usr/bin/env python3
"""Adjudicación regla C de la ronda Fable de s328, sin reescribir bytes previos.

Esta vez el runner SÍ registró su fila solo: fue una corrida `--standalone`, y
lo que falla en este proyecto es el modo EMPAREJADO (`TECH_DEBT #93`, dúo
secuencial). Aquí solo se rellenan los contadores y el veredicto, que es la
parte que le toca al adjudicador y que el runner deja en blanco a propósito.

Tiering (Protocolo 3): impacto MEDIO fuera de la zona de dolor
(corpus/idiomas/legacy/retrieval/esquema) ⇒ Fable sí, Sol no. Declarado aquí
para que la ausencia de Sol sea una decisión visible y no un olvido.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "evals/adversarial_review_log.jsonl"
TARGET_TS = "2026-08-20T06:10:23"

VERDICT = (
    "Regla C sobre 5 hallazgos de Fable (standalone; SIN Sol por tiering: "
    "impacto MEDIO fuera de zona de dolor). 5 CONFIRMADOS contra codigo, 0 FP. "
    "Severidad maxima: medio. Veredicto del revisor: NO SOLIDO hasta cerrar los "
    "tres medios — cerrados los cinco. "
    "F1 [medio] la claim de aislamiento de la puerta era FALSA hoy, no en "
    "potencia: `.entrar`, `.marca-puerta` y `.pie-puerta` no colgaban de "
    "`body.entrada`, y `class=\"entrar\"` YA se usa en la pagina de error "
    "(app.py:1025). Verificado con grep. Y era doble: al reescribir `.entrar` "
    "suelta le habia CAMBIADO EL LAYOUT a la pagina de error sin darme cuenta. "
    "Cierre: la regla original de `.entrar` restaurada para `_error`, todo lo de "
    "la puerta acotado bajo `body.entrada`, y la 404 re-fotografiada con "
    "Chromium para comprobar que volvio a su diseno. "
    "F2 [medio] el gate cazaba MI instancia, no la clase: (i) un SVG sin "
    "`viewBox` se saltaba con `continue` y dejaba el test de alineacion pasando "
    "EN VACIO; (ii) el fallback de columna hermana buscaba por NOMBRE DE CLASE "
    "(`.etiquetas`/`.etiqueta`), asi que otra implementacion de dos escalas con "
    "otros nombres pasaba en verde; (iii) solo cubre `barras()`. Cierre: la "
    "sonda ya no se apoya en nombres de clase —los rotulos de fuera se buscan "
    "como hojas-con-texto del subarbol del padre—, no se salta ningun SVG, y "
    "afirma que si hay SVG sin ancho natural medible es ROJO y no salto. (iii) "
    "se declara: no se puede gatear un tipo de grafico que aun no existe. "
    "F3 [medio] el gate podia quedar VERDE sin medir nada: un fallo de launch de "
    "Chromium en CI caia en `pytest.skip` y el job pasaba. Es el patron de "
    "cobertura-que-miente que #94 vino a cerrar, reintroducido dentro del propio "
    "arreglo de #94. Cierre: `PANEL_GEOMETRIA_EXIGIDA=1` en el workflow convierte "
    "«no hay navegador» en ROJO; en local sigue saltando. VERIFICADO en los tres "
    "modos: exigido-sin-navegador = 2 failed + 45 errors; no-exigido-sin-navegador "
    "= 47 skipped; normal = 41 passed. Para poder ejercitarlo hubo que hacer "
    "sobrescribible la ruta del navegador (`PANEL_CHROMIUM`): el primer intento "
    "con `PLAYWRIGHT_BROWSERS_PATH` no probaba nada porque la ruta estaba fija. "
    "F4 [menor] el control negativo («13 rojos con el render de s327») era prosa "
    "no reproducible: ese render ya no existe en el arbol, asi que la evidencia "
    "vivia en un comentario. Es la misma clase que el hallazgo critico de s327 "
    "(citar lo que el revisor no puede abrir). Cierre: el patron roto se "
    "reconstruye en una pagina sintetica VERSIONADA y dos tests exigen que la "
    "sonda la marque y que NO marque el render vigente — el discriminador queda "
    "auditable desde el repo para siempre. "
    "F5 [menor] el docstring de render.py decia CSP `script-src 'none'` cuando la "
    "cabecera real es `default-src 'none'`. Verificado en app.py:156. Corregido. "
    "NO VERIFICABLE por el revisor, y asi se queda: las cifras de Chromium "
    "(x2,29 y 264 px sobre el render de s327) son declaracion del autor — pero "
    "F4 arregla justo eso hacia adelante."
)


def main() -> int:
    raw = LOG.read_bytes()
    lines = raw.splitlines(keepends=True)
    ending = (b"\r\n" if lines[-1].endswith(b"\r\n")
              else b"\n" if lines[-1].endswith(b"\n") else b"")
    payload = lines[-1][: -len(ending)] if ending else lines[-1]
    row = json.loads(payload.decode("utf-8"))

    if row.get("ts") != TARGET_TS:
        raise RuntimeError("la revision s328 no es la ultima entrada del log")
    if row.get("duo_status") == "fable_only_adjudicado":
        print("S328_ADJUDICATION_ALREADY_APPLIED")
        return 0
    if row.get("duo_status") != "fable_only_complete_pending_adjudication":
        raise RuntimeError(f"estado inesperado: {row.get('duo_status')!r}")
    if row.get("model_contract_satisfied") is not True:
        raise RuntimeError("la fila no satisface el contrato de modelo")

    row.update(
        duo_status="fable_only_adjudicado",
        findings=5,
        confirmed=5,
        false_pos=0,
        severity_max="medio",
        verdict_notes=VERDICT,
    )
    recibo = row.get("fable_review") or {}
    recibo.update(findings=5, confirmed=5, false_pos=0, severity_max="medio")
    row["fable_review"] = recibo
    # Por qué no hubo Sol: decisión de tiering, no olvido (Protocolo 3).
    row["sol_omitido_motivo"] = (
        "tiering Protocolo 3: impacto MEDIO fuera de la zona de dolor "
        "(corpus/idiomas/legacy/retrieval/esquema) ⇒ Fable solo")

    lines[-1] = (json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                 .encode("utf-8") + ending)
    temporary = LOG.with_name(".adversarial_review_log.s328.tmp")
    try:
        temporary.write_bytes(b"".join(lines))
        os.replace(temporary, LOG)
    finally:
        if temporary.exists():
            temporary.unlink()
    print("S328_ADJUDICATION_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
