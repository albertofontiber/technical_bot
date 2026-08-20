# -*- coding: utf-8 -*-
"""Clasificador batch de preguntas (s326) — invocación manual con recibo.

Es el MISMO código que corre el seam del worker (`src/clasificacion.py`); este
script existe para las corridas que un humano decide: el backfill inicial tras
aplicar la 021, y la re-clasificación del histórico cuando la taxonomía sube de
versión (subir `version` en `config/taxonomia_preguntas.yaml` convierte todo
el histórico en pendiente — no hay modo «re-taxonomizar» aparte a propósito:
un solo camino, sin estados especiales).

Uso:
    python -m scripts.clasificar_preguntas --dry-run          # cuenta, no escribe
    python -m scripts.clasificar_preguntas --cap 500          # corrida real
    python -m scripts.clasificar_preguntas --receipt evals/s326_backfill_v1.json

Claves: SUPABASE_URL / SUPABASE_SERVICE_KEY (las del bot) y ANTHROPIC_API_KEY
(o ANTHROPIC_API_KEY_SCRIPTS, el nombre que usa el entorno cloud). Sin clave de
Anthropic clasifica SOLO por regla y cuenta el resto como `sin_llm` — corrida
honesta, no a medias en silencio.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clasificacion import (CAP_DEFECTO, MODELO_LLM,  # noqa: E402
                               Catalogo, ClasificacionNoDisponible,
                               cargar_taxonomia, construir_llm,
                               correr_pendientes, correr_sonda_eje,
                               huella_prompt)
from src.rag.retriever import (classify_model_manufacturer,  # noqa: E402
                               get_manufacturers_by_docs,
                               resolve_manufacturer_alias)


def _catalogo() -> Catalogo:
    """El conocimiento de catálogo, inyectado (frontera raiz→rag: el módulo de
    clasificación no importa rag; sus llamadores sí pueden)."""
    return Catalogo(
        nombres=[nombre for nombre, _docs in get_manufacturers_by_docs()],
        marca_de_modelo=classify_model_manufacturer,
        resolver_alias=resolve_manufacturer_alias,
    )

#: Precios de Haiku 4.5 ($/MTok entrada, salida) para el coste ESTIMADO del
#: recibo. Estimación declarada, no contabilidad.
_PRECIO_ENTRADA = 1.00
_PRECIO_SALIDA = 5.00

#: Dónde se apunta la última pasada de la sonda del eje. Versionado a
#: propósito: es el recibo de que un prompt concreto se midió antes de tocar
#: los datos, y sin él la pasada anterior sería un recuerdo.
_HUELLA = Path(__file__).parent.parent / "evals/sonda_eje_ultima_pasada.json"


def _prevuelo_del_eje(api_key: str, modelo: str, saltar: bool) -> tuple[bool, dict]:
    """La sonda del eje, ANTES de escribir nada. Devuelve (seguir, apunte).

    POR QUÉ AQUÍ Y NO EN CI (adjudicación de Alberto, s328e). El eje
    `es_pregunta` es la decisión más cara del clasificador: un `false`
    equivocado saca el mensaje de TODO el análisis y no deja rastro. Y esa
    conducta la sostiene el PROMPT, no el código — así que no hay test que la
    proteja. Este es el único camino por el que un prompt nuevo llega a los
    datos, así que el sitio donde ponerse delante es este, no un cron que
    alguien tiene que acordarse de mirar.

    CUÁNDO CORRE: solo si el prompt CAMBIÓ, medido por su huella. La huella es
    mejor señal que la versión del YAML, porque el contrato de «tocar una
    descripción obliga a subir version» es una convención que nadie impide
    saltarse; la huella no. Si el prompt es el mismo que ya pasó, no se gasta
    nada.
    """
    taxonomia = cargar_taxonomia()
    huella = huella_prompt(taxonomia)

    if not api_key:
        # Sin LLM el eje lo decide solo la regla dura, que es código y sí tiene
        # tests. No hay prompt que medir.
        return True, {"estado": "no_aplica_sin_llm"}
    if saltar:
        print("⚠️  PRE-VUELO OMITIDO por --sin-sonda: se va a escribir con un "
              "prompt SIN medir. Queda estampado en el recibo.")
        return True, {"estado": "OMITIDA_por_bandera", "huella_prompt": huella}

    if _HUELLA.exists():
        previo = json.loads(_HUELLA.read_text(encoding="utf-8"))
        if previo.get("huella_prompt") == huella and previo.get("pasa"):
            print(f"pre-vuelo del eje: el prompt no ha cambiado desde la última "
                  f"pasada ({previo.get('fecha', '?')}) — no se re-mide")
            return True, {"estado": "sin_cambios", "huella_prompt": huella}

    print("pre-vuelo del eje: el prompt CAMBIÓ (o no hay pasada previa) — "
          f"midiendo {12} casos contra {modelo}…")
    resultado = correr_sonda_eje(construir_llm(api_key, modelo), taxonomia)
    print(f"  preguntas sin signos reconocidas: "
          f"{resultado['preguntas_reconocidas']}/{resultado['preguntas_totales']} · "
          f"controles limpios: "
          f"{resultado['controles_limpios']}/{resultado['controles_totales']}")
    if not resultado["pasa"]:
        print("\n⛔ EL EJE HA REGRESADO — no se escribe NADA.", file=sys.stderr)
        for caso in resultado["no_reconocidas"]:
            print(f"   no reconocida como pregunta: «{caso}»", file=sys.stderr)
        for caso in resultado["falsos_positivos"]:
            print(f"   contada como pregunta y no lo es: «{caso}»", file=sys.stderr)
        print("\nEl prompt nuevo decide el eje peor que el anterior. Arréglalo, "
              "o —si el criterio ha cambiado a propósito— revisa los casos "
              "congelados en `src/clasificacion.py` y vuelve a correr.\n"
              "Para escribir igualmente, a sabiendas: --sin-sonda.", file=sys.stderr)
        return False, {"estado": "REGRESION", **resultado}

    _HUELLA.parent.mkdir(parents=True, exist_ok=True)
    _HUELLA.write_text(json.dumps(
        {"fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
         "modelo": modelo, **resultado}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"  pasa · apuntado en {_HUELLA.relative_to(_HUELLA.parent.parent)}")
    return True, {"estado": "pasa", "huella_prompt": huella}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cap", type=int, default=CAP_DEFECTO,
                        help=f"máximo de filas a examinar (default {CAP_DEFECTO})")
    parser.add_argument("--dry-run", action="store_true",
                        help="clasifica pero NO escribe (recibo igual)")
    parser.add_argument("--modelo", default=MODELO_LLM,
                        help=f"modelo del LLM (default {MODELO_LLM})")
    parser.add_argument("--receipt", type=Path, default=None,
                        help="ruta donde volcar el recibo JSON")
    parser.add_argument("--sin-sonda", action="store_true",
                        help="salta el pre-vuelo del eje (queda en el recibo)")
    argumentos = parser.parse_args()

    api_key = (os.getenv("ANTHROPIC_API_KEY")
               or os.getenv("ANTHROPIC_API_KEY_SCRIPTS") or "")
    if not api_key:
        print("AVISO: sin ANTHROPIC_API_KEY — solo clasificación por regla; "
              "el resto quedará pendiente (sin_llm).")

    seguir, apunte = _prevuelo_del_eje(api_key, argumentos.modelo,
                                      argumentos.sin_sonda)
    if not seguir:
        return 2

    try:
        recibo = correr_pendientes(argumentos.cap, catalogo=_catalogo(),
                                   api_key=api_key or None,
                                   modelo=argumentos.modelo,
                                   dry_run=argumentos.dry_run)
    except ClasificacionNoDisponible as exc:
        print(f"NO DISPONIBLE: {exc}")
        print("¿Está aplicada migrations/021_query_clasificacion.sql y hay "
              "credenciales de Supabase en el entorno?")
        return 1

    recibo["sonda_eje"] = apunte
    recibo["coste_estimado_usd"] = round(
        recibo["tokens_entrada"] / 1e6 * _PRECIO_ENTRADA
        + recibo["tokens_salida"] / 1e6 * _PRECIO_SALIDA, 4)
    print(json.dumps(recibo, indent=2, ensure_ascii=False))
    if argumentos.receipt:
        argumentos.receipt.parent.mkdir(parents=True, exist_ok=True)
        argumentos.receipt.write_text(
            json.dumps(recibo, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"recibo → {argumentos.receipt}")
    if recibo["llm_fallos"]:
        print(f"AVISO: {recibo['llm_fallos']} fila(s) quedaron pendientes "
              f"(respuesta LLM inválida) — se reintentan en la próxima corrida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
