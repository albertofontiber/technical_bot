"""s324e — INSIGHTS de los errores del bot: qué falla, dónde y sobre qué.

Para qué sirve. `bot_health_report` responde «¿cuántos errores?» (una cifra:
`filas_error`). Esto responde las preguntas con las que se decide qué arreglar:

    · ¿de qué CLASE son? (red, saturación del LLM, fallo real, transporte,
      dato ausente, defecto nuestro) — separa «hay que esperar» de «hay que
      arreglar código»;
    · ¿en qué MÓDULO:LÍNEA nacen? — la cola de trabajo, ordenada;
    · ¿en qué DÍA? — un pico contra un goteo son problemas distintos;
    · ¿qué PREGUNTAS los provocan (top 5)? — el puente al gold: una pregunta que
      rompe el bot dos veces es material de eval, no una anécdota;
    · ¿a cuántos técnicos se les quedó el bot MUDO? — la métrica del piloto.

Fuentes, y por qué DOS. Lee `bot_errors` (migración 015) y, además, las filas
heredadas de `query_logs` con `source='error'` (s286). No es redundancia: hasta
que Alberto aplique la 015 la primera no existe, y el histórico previo solo vive
en la segunda. El informe declara SIEMPRE de dónde salió cada cifra en vez de
mezclarlas en un total que no se podría interpretar.

Estados que sabe distinguir (y dice cuál es):
    · tabla ausente        → lo dice, informa igual con lo heredado, sale 0;
    · tabla vacía          → «0 incidencias», sale 0 (no es un fallo);
    · sin credenciales     → lo dice y sale 2 (no aparenta haber medido);
    · fallo de red al leer → lo dice y sale 2.

Uso:
    python -m scripts.s324e_bot_errores_insights                # últimos 7 días
    python -m scripts.s324e_bot_errores_insights --days 30
    python -m scripts.s324e_bot_errores_insights --all
    python -m scripts.s324e_bot_errores_insights --top 10
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY  # noqa: E402


def _consola_tolerante() -> None:
    """Que un carácter raro no tumbe el informe.

    Cazado en el smoke real de s324e: la consola de Windows abre en cp1252 y el
    `print` de un emoji reventaba con `UnicodeEncodeError` — un informe de
    errores que falla al imprimirse es exactamente la clase de ironía que este
    trabajo existe para evitar. Los símbolos propios ya se escriben en ASCII;
    esto cubre lo que NO controlamos: el top-5 son preguntas escritas por
    técnicos y pueden traer cualquier cosa.
    """
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


_consola_tolerante()

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
}

#: Marca de que la tabla no existe todavía — se distingue de «vacía» a
#: propósito: son dos acciones distintas (aplicar la migración vs celebrarlo).
TABLA_AUSENTE = "__tabla_ausente__"

#: Cuánto de la pregunta se enseña en el listado. Corto: el informe es para ver
#: patrones, y cada carácter de más es texto libre de un técnico en una consola.
_RECORTE_PREGUNTA = 90


class SinCredenciales(RuntimeError):
    """Ni URL ni clave de Supabase: no se puede leer nada."""


# ------------------------------------------------------------------- lectura


def _paginar(tabla: str, select: str, since_iso: str | None,
             extra: dict | None = None) -> list[dict] | str:
    """Todas las filas de `tabla`, o `TABLA_AUSENTE` si PostgREST dice que no
    existe. Cualquier otro error HTTP se propaga: no se disimula."""
    filas: list[dict] = []
    tam = 1000
    offset = 0
    while True:
        params = {
            "select": select,
            "order": "created_at.desc",
            "limit": str(tam),
            "offset": str(offset),
        }
        if since_iso:
            params["created_at"] = f"gte.{since_iso}"
        params.update(extra or {})
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{SUPABASE_URL}/rest/v1/{tabla}", headers=_HEADERS, params=params
            )
        if resp.status_code in (404, 400):
            try:
                codigo = str((resp.json() or {}).get("code") or "")
            except Exception:                                # noqa: BLE001
                codigo = ""
            if codigo in ("PGRST205", "PGRST106", "42P01") or resp.status_code == 404:
                return TABLA_AUSENTE
        resp.raise_for_status()
        lote = resp.json()
        filas.extend(lote)
        if len(lote) < tam:
            return filas
        offset += tam


def leer(since_iso: str | None) -> tuple[list[dict] | str, list[dict]]:
    """(incidencias de `bot_errors` | TABLA_AUSENTE, filas de error heredadas)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise SinCredenciales(
            "faltan SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno"
        )
    incidencias = _paginar(
        "bot_errors",
        "codigo,clase,severidad,reintentable,tipo_excepcion,etapa,origen,"
        "mensaje_corto,usuario_avisado,bot_version,created_at,"
        "query_logs(query,telegram_user_id)",
        since_iso,
    )
    heredadas = _paginar(
        "query_logs",
        "query,response,telegram_user_id,created_at",
        since_iso,
        extra={"source": "eq.error"},
    )
    return incidencias, (heredadas if isinstance(heredadas, list) else [])


# ------------------------------------------------------------------ agregación
# Función PURA (sin red): es la que prueban los tests, igual que `summarize` en
# bot_health_report. Todo lo de arriba es I/O y todo lo de abajo es impresión.


def _dia(fila: dict) -> str:
    valor = str(fila.get("created_at") or "")
    return valor[:10] or "(sin fecha)"


def _pregunta_de(inc: dict) -> str | None:
    """La consulta enlazada, si la hay. Puede faltar por tres motivos legítimos:
    el turno no tenía consulta (comando/callback/job), el autor no había
    aceptado los términos, o la fila padre ya se borró por retención."""
    padre = inc.get("query_logs")
    if isinstance(padre, list):
        padre = padre[0] if padre else None
    if not isinstance(padre, dict):
        return None
    consulta = padre.get("query")
    return consulta if isinstance(consulta, str) and consulta.strip() else None


def agregar(incidencias: list[dict], heredadas: list[dict], *,
            top: int = 5) -> dict:
    """Las cifras del informe. Pura y tolerante a campos ausentes."""
    por_clase = Counter()
    por_severidad = Counter()
    por_origen = Counter()
    por_dia = Counter()
    por_tipo = Counter()
    por_etapa = Counter()
    preguntas = Counter()
    sin_avisar = 0
    afectados: set = set()

    for inc in incidencias:
        por_clase[inc.get("clase") or "(sin clase)"] += 1
        por_severidad[inc.get("severidad") or "(sin severidad)"] += 1
        por_origen[inc.get("origen") or "(sin origen)"] += 1
        por_dia[_dia(inc)] += 1
        por_tipo[inc.get("tipo_excepcion") or "(sin tipo)"] += 1
        por_etapa[inc.get("etapa") or "(sin etapa)"] += 1
        if inc.get("usuario_avisado") is False:
            sin_avisar += 1
        consulta = _pregunta_de(inc)
        if consulta:
            # Normalizada: la MISMA pregunta escrita con otro espaciado o en
            # otra caja es la misma pregunta para contar patrones.
            preguntas[" ".join(consulta.split()).lower()] += 1
        padre = inc.get("query_logs")
        if isinstance(padre, list):
            padre = padre[0] if padre else None
        if isinstance(padre, dict) and padre.get("telegram_user_id"):
            afectados.add(padre["telegram_user_id"])

    # Heredadas: `response` guarda 'TipoDeExcepcion@etapa'. Se parsea con
    # cuidado y SIN fingir clase — esas filas no la tienen, y asignarles una
    # inventaría el dato que justifica la tabla nueva.
    heredadas_por_tipo = Counter()
    heredadas_por_dia = Counter()
    heredadas_preguntas = Counter()
    for fila in heredadas:
        marca = str(fila.get("response") or "").strip()
        tipo, _, etapa = marca.partition("@")
        heredadas_por_tipo[f"{tipo or '(sin tipo)'}@{etapa or '(sin etapa)'}"] += 1
        heredadas_por_dia[_dia(fila)] += 1
        consulta = fila.get("query")
        if isinstance(consulta, str) and consulta.strip():
            heredadas_preguntas[" ".join(consulta.split()).lower()] += 1

    return {
        "n_incidencias": len(incidencias),
        "n_heredadas": len(heredadas),
        "por_clase": dict(por_clase.most_common()),
        "por_severidad": dict(por_severidad.most_common()),
        "por_origen": dict(por_origen.most_common()),
        "por_dia": dict(sorted(por_dia.items())),
        "por_tipo": dict(por_tipo.most_common()),
        "por_etapa": dict(por_etapa.most_common()),
        "top_preguntas": preguntas.most_common(top),
        "sin_avisar": sin_avisar,
        "tecnicos_afectados": len(afectados),
        "heredadas_por_tipo": dict(heredadas_por_tipo.most_common()),
        "heredadas_por_dia": dict(sorted(heredadas_por_dia.items())),
        "heredadas_top_preguntas": heredadas_preguntas.most_common(top),
    }


# ------------------------------------------------------------------ impresión


def _bloque(titulo: str, conteos: dict, *, limite: int | None = None) -> None:
    print(f"\n{titulo}")
    if not conteos:
        print("  (ninguno)")
        return
    filas = list(conteos.items())
    if limite:
        filas = filas[:limite]
    ancho = max(len(str(k)) for k, _ in filas)
    for clave, n in filas:
        print(f"  {str(clave).ljust(ancho)}  {n}")


def imprimir(resumen: dict, *, label: str, tabla_ausente: bool,
             top: int) -> None:
    print(f"\n=== Errores del bot — {label} ===")

    if tabla_ausente:
        print(
            "\nAVISO: `bot_errors` NO existe todavía — falta aplicar "
            "migrations/015_bot_errores.sql.\n"
            "    El bot NO está roto — registra los errores DEGRADADOS en "
            "query_logs (source='error').\n"
            "    Lo que falta hasta aplicarla: clase de fallo, módulo de "
            "origen, severidad y si el técnico recibió aviso."
        )
    else:
        print(f"\nIncidencias registradas: {resumen['n_incidencias']}")
        if resumen["n_incidencias"] == 0:
            print("  (ninguna en la ventana — no hay nada que arreglar aquí)")
        else:
            print(
                f"Técnicos afectados (identificables): "
                f"{resumen['tecnicos_afectados']}"
            )
            print(
                f"Incidencias en las que el técnico NO recibió aviso: "
                f"{resumen['sin_avisar']}"
                + ("  <- el fallo que este trabajo existe para que sea 0"
                   if resumen["sin_avisar"] else "")
            )
            _bloque("Por CLASE de fallo:", resumen["por_clase"])
            _bloque("Por SEVERIDAD:", resumen["por_severidad"])
            _bloque("Por MÓDULO:LÍNEA de origen (la cola de trabajo):",
                    resumen["por_origen"], limite=10)
            _bloque("Por ETAPA:", resumen["por_etapa"])
            _bloque("Por TIPO de excepción:", resumen["por_tipo"], limite=10)
            _bloque("Por DÍA:", resumen["por_dia"])

            print(f"\nLas {top} preguntas que más fallan:")
            if not resumen["top_preguntas"]:
                print("  (ninguna incidencia tiene consulta enlazada)")
            for consulta, n in resumen["top_preguntas"]:
                recorte = consulta[:_RECORTE_PREGUNTA]
                sufijo = "…" if len(consulta) > _RECORTE_PREGUNTA else ""
                print(f"  {n}×  {recorte}{sufijo}")

    print(f"\n--- Filas de error HEREDADAS (query_logs, s286): "
          f"{resumen['n_heredadas']} ---")
    if resumen["n_heredadas"]:
        _bloque("Por marca `Tipo@etapa`:", resumen["heredadas_por_tipo"],
                limite=10)
        _bloque("Por DÍA:", resumen["heredadas_por_dia"])
        print(f"\nPreguntas que más fallan (heredadas, top {top}):")
        for consulta, n in resumen["heredadas_top_preguntas"]:
            recorte = consulta[:_RECORTE_PREGUNTA]
            sufijo = "…" if len(consulta) > _RECORTE_PREGUNTA else ""
            print(f"  {n}×  {recorte}{sufijo}")

    print(
        "\nNota: las dos fuentes NO se suman. Desde que la 015 esté aplicada, "
        "cada error escribe en AMBAS\n(la consulta en `query_logs`, el "
        "diagnóstico en `bot_errors`) y sumarlas contaría cada fallo dos veces."
    )


def _construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Insights de los errores del bot (s324e)"
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--all", action="store_true", help="histórico completo")
    parser.add_argument("--top", type=int, default=5,
                        help="cuántas preguntas listar (default 5)")
    return parser


def main() -> int:
    args = _construir_parser().parse_args()
    if args.all:
        since_iso, label = None, "histórico completo"
    else:
        since = datetime.now(timezone.utc) - timedelta(days=args.days)
        since_iso, label = since.isoformat(), f"últimos {args.days} días"

    try:
        incidencias, heredadas = leer(since_iso)
    except SinCredenciales as exc:
        print(f"\nNO SE HA PODIDO LEER NADA: {exc}")
        print("Sin credenciales no hay informe — y un informe vacío se "
              "confundiría con «no hay errores».")
        return 2
    except Exception as exc:                                 # noqa: BLE001
        print(f"\nNO SE HA PODIDO LEER NADA ({type(exc).__name__}): {exc}")
        return 2

    tabla_ausente = incidencias == TABLA_AUSENTE
    resumen = agregar(
        [] if tabla_ausente else incidencias, heredadas, top=args.top
    )
    imprimir(resumen, label=label, tabla_ausente=tabla_ausente, top=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
