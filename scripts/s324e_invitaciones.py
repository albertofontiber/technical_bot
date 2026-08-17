# -*- coding: utf-8 -*-
"""s324e — La herramienta de Alberto para el control de acceso del piloto:
emitir invitaciones, ver en qué estado están y quitar acceso.

Todo lo que hay que saber para invitar a un DG:

    python -m scripts.s324e_invitaciones generar --nota "Juan Perez, DG de Acme"

Imprime UNA vez el enlace `https://t.me/<bot>?start=<token>`. Se lo mandas por
donde quieras. Cuando lo pulsa, queda dado de alta y el bot le enseña los
terminos. El enlace es de un solo uso, caduca (2 dias por defecto, 7 como
maximo) y se puede anular antes.

    python -m scripts.s324e_invitaciones listar          # pendientes/usadas/caducadas
    python -m scripts.s324e_invitaciones allowlist       # quien tiene acceso hoy
    python -m scripts.s324e_invitaciones alta 12345678 --nota "Alberto"
    python -m scripts.s324e_invitaciones revocar-invitacion 3f2a
    python -m scripts.s324e_invitaciones revocar-acceso 12345678 --motivo "fin del piloto"

EL TOKEN SE ENSENA UNA SOLA VEZ. En Supabase se guarda su SHA-256, no el token,
asi que quien lea la tabla de SOLO LECTURA (una copia de seguridad, la consola,
un export) NO obtiene invitaciones utilizables. Precision que el duo obligo a
hacer: esto NO protege de la SERVICE KEY - quien la tenga puede insertarse una
fila de allowlist directamente, asi que esa credencial sigue siendo la frontera
real. Si pierdes un enlace, anulalo y emite otro: no hay forma de recuperarlo, y
ese es el diseno.

ESTADOS QUE SABE DISTINGUIR (y dice cual es), igual que el informe de errores:
    - migracion 016 sin aplicar -> lo dice, con la ruta del fichero;
    - tabla vacia               -> «no hay invitaciones», no es un fallo;
    - sin credenciales          -> lo dice y sale 2 (no aparenta haber medido).

CODIGOS DE SALIDA:
    0  la accion se completo (o no habia nada que hacer/listar);
    2  no se pudo actuar - sin credenciales, sin migracion, o no se encontro lo
       que se pedia. NUNCA se dice «hecho» sin haberlo hecho.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot import access                                      # noqa: E402
from src.config import SUPABASE_URL, SUPABASE_SERVICE_KEY       # noqa: E402


def _consola_tolerante() -> None:
    """Que un caracter raro no tumbe la herramienta (la consola de Windows abre
    en cp1252 y las notas las escribe una persona). Misma leccion que el informe
    de errores de s324e."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except Exception:                                    # noqa: BLE001
            pass


_consola_tolerante()

_HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
}

_MIGRACION = "migrations/016_allowlist_invitaciones.sql"
_TIMEOUT = 30.0


class SinCredenciales(RuntimeError):
    """Ni URL ni clave de Supabase: no se puede leer ni escribir nada."""


class TablaAusente(RuntimeError):
    """La migracion 016 no esta aplicada todavia."""


def _exigir_credenciales() -> None:
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise SinCredenciales(
            "faltan SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno"
        )


def _tabla_ausente(resp: httpx.Response) -> bool:
    """¿PostgREST dice que la tabla no existe? Mismo criterio que `logging_db`:
    se distingue de cualquier otro 4xx porque «la migracion aun no esta
    aplicada» es un estado ESPERADO de este repo."""
    if resp.status_code not in (404, 400):
        return False
    try:
        codigo = str((resp.json() or {}).get("code") or "")
    except Exception:                                        # noqa: BLE001
        return resp.status_code == 404
    return codigo in ("PGRST205", "PGRST106", "42P01") or resp.status_code == 404


def _pedir(metodo: str, tabla: str, *, headers: dict | None = None,
           **kwargs) -> list[dict]:
    """Una peticion a PostgREST. Traduce los dos estados esperados a excepciones
    con nombre y deja escapar el resto: un 401 o un 500 no se disimulan."""
    _exigir_credenciales()
    cabeceras = headers or {**_HEADERS, "Prefer": "return=representation"}
    with httpx.Client(timeout=_TIMEOUT) as cliente:
        resp = cliente.request(
            metodo, f"{SUPABASE_URL}/rest/v1/{tabla}", headers=cabeceras, **kwargs
        )
    if _tabla_ausente(resp):
        raise TablaAusente(tabla)
    resp.raise_for_status()
    if resp.status_code == 204 or not resp.content:
        return []
    datos = resp.json()
    return datos if isinstance(datos, list) else [datos]


# ------------------------------------------------------------------ formato


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(momento: datetime) -> str:
    """ISO con `Z`. Se evita el `+00:00` a proposito: viaja como parametro de
    consulta y el `+` es ambiguo al codificar una URL."""
    return momento.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _fecha(valor: str | None) -> str:
    """`'2026-08-17T10:00:00Z'` → `'2026-08-17 10:00'`, o `'-'`."""
    if not valor:
        return "-"
    try:
        return (datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
                .astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M"))
    except ValueError:
        return str(valor)[:16]


# El estado DERIVADO de una invitacion vive en `access.estado_invitacion` desde
# s324f. Estaba aqui como `_estado_invitacion` y se subio a la hoja pura cuando
# el panel web paso a ser un SEGUNDO lector de las mismas filas: dos copias de
# la regla «usada manda sobre caducada» son una divergencia esperando su turno.
# Aqui no queda alias: se llama a la hoja, que es la unica fuente.


def _corto(texto: object, ancho: int) -> str:
    valor = "-" if texto in (None, "") else str(texto)
    return valor if len(valor) <= ancho else valor[: ancho - 1] + "..."


def _operador(explicito: str | None) -> str:
    """Quien firma la accion. Se toma del argumento, del usuario del sistema o,
    en ultimo caso, una etiqueta generica - pero SIEMPRE hay firma: la traza
    «quien dio de alta a quien» es la mitad del requisito."""
    if explicito:
        return explicito.strip()
    try:
        return getpass.getuser() or "operador"
    except Exception:                                        # noqa: BLE001
        return "operador"


def _dias_validos(bruto: str) -> int:
    """Caducidad en dias, ACOTADA de verdad.

    Antes `--dias` aceptaba cualquier entero mientras la propuesta afirmaba «se
    acota a 7 dias» (duo, menor 7): un `--dias 3650` la desmentia. La cota vive
    en los DOS lados —aqui, para dar un error legible, y como CHECK en la 016,
    que es la que de verdad la garantiza porque el script no es el unico
    cliente posible de la tabla.
    """
    try:
        dias = int(bruto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{bruto!r} no es un numero de dias") from None
    if not 1 <= dias <= access.DIAS_CADUCIDAD_MAX:
        raise argparse.ArgumentTypeError(
            f"la caducidad debe estar entre 1 y {access.DIAS_CADUCIDAD_MAX} dias "
            f"(pediste {dias}). Una invitacion de vida larga es justo el enlace "
            f"que se queda olvidado en un chat."
        )
    return dias


def _nombre_del_bot(explicito: str | None) -> str | None:
    import os

    return (explicito or os.getenv("TELEGRAM_BOT_USERNAME") or "").lstrip("@") or None


# ---------------------------------------------------------------- acciones


def cmd_generar(args) -> int:
    expira = _ahora() + timedelta(days=args.dias)
    token = access.token_nuevo()
    filas = _pedir(
        "POST", "bot_invitaciones",
        json={
            "token_hash": access.hash_token(token),
            "nota": args.nota,
            "creada_por": _operador(args.por),
            "expira_at": _iso(expira),
        },
    )
    if not filas:
        print("No se pudo crear la invitacion (la base no devolvio la fila).")
        return 2
    invitacion = filas[0]
    bot = _nombre_del_bot(args.bot)
    enlace = (access.enlace_invitacion(bot, token) if bot
              else f"https://t.me/<NOMBRE_DEL_BOT>?start={token}")

    print()
    print("  INVITACION CREADA")
    print(f"  id      : {invitacion.get('id')}")
    print(f"  para    : {args.nota or '(sin nota)'}")
    print(f"  emitida : {_operador(args.por)}")
    print(f"  caduca  : {_fecha(invitacion.get('expira_at'))} UTC "
          f"({args.dias} dias; el maximo son {access.DIAS_CADUCIDAD_MAX})")
    print()
    print("  Enlace (mandaselo a esa persona):")
    print(f"    {enlace}")
    print()
    if not bot:
        print("  OJO: sustituye <NOMBRE_DEL_BOT> por el usuario del bot, o pasa")
        print("       --bot PCI_Soporte_tecnico_bot (o TELEGRAM_BOT_USERNAME).")
        print()
    print("  Este enlace NO se puede volver a mostrar: en la base solo esta su")
    print("  huella. Si lo pierdes, anula la invitacion y emite otra.")
    print("  Es de UN SOLO USO: quien lo pulse primero se queda el acceso.")
    print()
    return 0


def cmd_listar(args) -> int:
    filas = _pedir(
        "GET", "bot_invitaciones",
        params={"select": "id,nota,creada_por,creada_at,expira_at,canjeada_at,"
                          "canjeada_por,revocada_at",
                "order": "creada_at.desc"},
    )
    ahora = _ahora()
    conteo: dict[str, int] = {}
    visibles = []
    for fila in filas:
        estado = access.estado_invitacion(fila, ahora)
        conteo[estado] = conteo.get(estado, 0) + 1
        if args.todas or estado == "pendiente":
            visibles.append((estado, fila))

    if not filas:
        print("No hay invitaciones todavia. Crea una con `generar --nota \"...\"`.")
        return 0

    print()
    print(f"  {'ESTADO':<10} {'ID':<10} {'PARA':<32} {'CADUCA':<17} "
          f"{'CANJEADA POR':<14} EMITIDA POR")
    print("  " + "-" * 100)
    for estado, fila in visibles:
        print(f"  {estado:<10} {str(fila.get('id'))[:8]:<10} "
              f"{_corto(fila.get('nota'), 32):<32} "
              f"{_fecha(fila.get('expira_at')):<17} "
              f"{_corto(fila.get('canjeada_por'), 14):<14} "
              f"{_corto(fila.get('creada_por'), 16)}")
    if not visibles:
        print("  (ninguna pendiente - usa --todas para ver el historico)")
    print()
    print("  Total: " + ", ".join(f"{n} {estado}"
                                  for estado, n in sorted(conteo.items())))
    if not args.todas:
        print("  (se muestran solo las PENDIENTES; --todas para el resto)")
    print()
    return 0


def cmd_allowlist(args) -> int:
    filas = _pedir(
        "GET", "bot_allowlist",
        params={"select": "telegram_user_id,nota,origen,alta_por,alta_at,"
                          "revocado_at,revocado_por,motivo_revocacion",
                "order": "alta_at.desc"},
    )
    if not filas:
        print("La allowlist esta VACIA: con BOT_ALLOWLIST=on no entraria nadie")
        print("salvo los ids de BOT_ALLOWLIST_BOOTSTRAP. Revisa la FASE B de la")
        print(f"migracion ({_MIGRACION}), que da de alta a quien ya usaba el bot.")
        return 0

    activos = [f for f in filas if not f.get("revocado_at")]
    print()
    print(f"  {'ESTADO':<9} {'TELEGRAM ID':<13} {'QUIEN ES':<34} "
          f"{'ORIGEN':<12} {'ALTA':<17} ALTA POR")
    print("  " + "-" * 104)
    for fila in filas:
        if fila.get("revocado_at") and not args.todas:
            continue
        estado = "revocado" if fila.get("revocado_at") else "activo"
        print(f"  {estado:<9} {str(fila.get('telegram_user_id')):<13} "
              f"{_corto(fila.get('nota'), 34):<34} "
              f"{_corto(fila.get('origen'), 12):<12} "
              f"{_fecha(fila.get('alta_at')):<17} "
              f"{_corto(fila.get('alta_por'), 16)}")
    print()
    print(f"  {len(activos)} con acceso - {len(filas) - len(activos)} revocados")
    if not args.todas:
        print("  (--todas incluye los revocados)")
    print()
    return 0


def cmd_alta(args) -> int:
    """Alta directa, sin invitacion. Para el bootstrap y para cuando ya conoces
    el id (te lo dice `listar` tras un canje, o el propio Telegram)."""
    filas = _pedir(
        "POST", "bot_allowlist?on_conflict=telegram_user_id",
        headers={**_HEADERS, "Prefer": "resolution=merge-duplicates,"
                                       "return=representation"},
        json={
            "telegram_user_id": args.telegram_user_id,
            "nota": args.nota,
            "origen": "manual",
            "alta_por": _operador(args.por),
            "alta_at": _iso(_ahora()),
            "revocado_at": None,
            "revocado_por": None,
            "motivo_revocacion": None,
        },
    )
    if not filas:
        print("No se pudo dar de alta (la base no devolvio la fila).")
        return 2
    print(f"Alta OK: {args.telegram_user_id} - {args.nota or '(sin nota)'} "
          f"(por {_operador(args.por)})")
    print("Efecto en el bot: inmediato para quien no estuviera ya cacheado como")
    print(f"denegado; en el peor caso {int(access.TTL_NEGATIVO_S)} s.")
    return 0


def cmd_revocar_invitacion(args) -> int:
    """Anula una invitacion PENDIENTE. Acepta el prefijo del id (lo que enseña
    `listar`) para no tener que copiar un UUID entero a mano."""
    # El prefijo se filtra AQUI y no en la consulta: PostgREST traduciria
    # `id=like.3f2a%` a un `LIKE` sobre una columna `uuid`, y Postgres no tiene
    # ese operador (`uuid ~~ unknown`). A la escala del piloto traer la tabla
    # entera es gratis, y funciona con cualquier version de PostgREST.
    prefijo = str(args.id).strip().lower()
    candidatas = [
        fila for fila in _pedir(
            "GET", "bot_invitaciones",
            params={"select": "id,nota,canjeada_at,revocada_at,expira_at"},
        )
        if str(fila.get("id", "")).lower().startswith(prefijo)
    ]
    if not candidatas:
        print(f"No hay ninguna invitacion cuyo id empiece por {args.id!r}.")
        return 2
    if len(candidatas) > 1:
        print(f"{args.id!r} es ambiguo ({len(candidatas)} invitaciones). "
              f"Usa mas caracteres del id.")
        return 2
    invitacion = candidatas[0]
    if invitacion.get("canjeada_at"):
        print("Esa invitacion YA se canjeo: anularla no quita el acceso.")
        print("Para quitarlo: `revocar-acceso <telegram_user_id>` "
              "(el id sale en `listar --todas`).")
        return 2
    _pedir("PATCH", "bot_invitaciones",
           params={"id": f"eq.{invitacion['id']}"},
           json={"revocada_at": _iso(_ahora())})
    print(f"Invitacion anulada: {invitacion['id']} "
          f"- {invitacion.get('nota') or '(sin nota)'}")
    return 0


def cmd_revocar_acceso(args) -> int:
    ahora = _ahora()
    filas = _pedir(
        "PATCH", "bot_allowlist",
        params={"telegram_user_id": f"eq.{args.telegram_user_id}",
                "revocado_at": "is.null"},
        json={"revocado_at": _iso(ahora),
              "revocado_por": _operador(args.por),
              "motivo_revocacion": args.motivo},
    )
    if not filas:
        print(f"{args.telegram_user_id} no tiene acceso activo "
              f"(no esta en la allowlist o ya estaba revocado).")
        return 2
    print(f"Acceso revocado: {args.telegram_user_id} "
          f"- {filas[0].get('nota') or '(sin nota)'}")
    # La latencia REAL, con sus dos casos. Antes esta linea decia «hasta 10
    # minutos» a secas y era el caso bueno: con Supabase caido, la puerta sirve
    # el ultimo SI confirmado durante la ventana de gracia, asi que el peor caso
    # es la suma. Se dicen los dos numeros porque el que decide es Alberto.
    # Los dos plazos NO se suman: la gracia se cuenta desde la ULTIMA
    # confirmacion de la base, no desde que caduca la cache, asi que el peor
    # caso es el mayor de los dos. Cifras DERIVADAS del diseno y ancladas en
    # test offline (no hay observacion end-to-end contra Telegram).
    print(f"Efecto en el bot: hasta {int(access.TTL_FRESCO_S / 60)} min con la "
          f"base sana (cache de la puerta), y hasta "
          f"{int(access.GRACIA_DEGRADADA_S / 60)} min si Supabase esta caido "
          f"(gracia degradada). Sin reiniciar el worker.")
    print("Efecto INMEDIATO: reinicia el servicio en Railway (vacia la cache).")
    print("Un turno ya en vuelo termina: se corta a partir del siguiente mensaje.")

    # El agujero que la revocacion NO cubre y hay que decir en voz alta.
    if args.telegram_user_id in access.ids_bootstrap():
        print()
        print(f"!! {args.telegram_user_id} esta en BOT_ALLOWLIST_BOOTSTRAP: la")
        print("   puerta lo deja pasar SIN mirar la base, asi que esta revocacion")
        print("   NO le afecta. Quitalo de la variable en Railway.")
    else:
        print("(Si ese id estuviera en BOT_ALLOWLIST_BOOTSTRAP de Railway, esto")
        print(" no le afectaria: esa lista no pasa por la base.)")

    # El hueco que hay que decir en voz alta: una invitacion PENDIENTE emitida
    # para esa misma persona sigue viva y le devolveria el acceso al pulsarla.
    # No se puede cruzar automaticamente (una invitacion sin canjear no tiene
    # `telegram_user_id`), asi que se enumeran para que decida una persona.
    pendientes = [
        f for f in _pedir("GET", "bot_invitaciones",
                          params={"select": "id,nota,expira_at,canjeada_at,"
                                            "revocada_at"})
        if access.estado_invitacion(f, ahora) == "pendiente"
    ]
    if pendientes:
        print()
        print(f"OJO: hay {len(pendientes)} invitacion(es) PENDIENTES. Si alguna")
        print("era para esta persona, anulala tambien o volvera a entrar:")
        for fila in pendientes:
            print(f"  - {str(fila['id'])[:8]}  {_corto(fila.get('nota'), 40)}")
    return 0


# -------------------------------------------------------------------- main


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.s324e_invitaciones",
        description="Control de acceso del piloto: invitaciones y allowlist.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    generar = sub.add_parser("generar", help="emite una invitacion de un solo uso")
    generar.add_argument("--nota", required=True,
                         help="para quien es (nombre y cargo) - obligatorio: sin "
                              "esto el listado no se puede auditar")
    generar.add_argument("--dias", type=_dias_validos,
                         default=access.DIAS_CADUCIDAD_DEFECTO,
                         help=f"caducidad en dias (por defecto "
                              f"{access.DIAS_CADUCIDAD_DEFECTO}, maximo "
                              f"{access.DIAS_CADUCIDAD_MAX})")
    generar.add_argument("--bot", default=None,
                         help="usuario del bot para el enlace "
                              "(o TELEGRAM_BOT_USERNAME)")
    generar.add_argument("--por", default=None, help="quien la emite")
    generar.set_defaults(funcion=cmd_generar)

    listar = sub.add_parser("listar", help="invitaciones y su estado")
    listar.add_argument("--todas", action="store_true",
                        help="incluye usadas, caducadas y anuladas")
    listar.set_defaults(funcion=cmd_listar)

    lista = sub.add_parser("allowlist", help="quien puede usar el bot hoy")
    lista.add_argument("--todas", action="store_true",
                       help="incluye los revocados")
    lista.set_defaults(funcion=cmd_allowlist)

    alta = sub.add_parser("alta", help="alta directa, sin invitacion")
    alta.add_argument("telegram_user_id", type=int)
    alta.add_argument("--nota", required=True, help="quien es")
    alta.add_argument("--por", default=None)
    alta.set_defaults(funcion=cmd_alta)

    rev_inv = sub.add_parser("revocar-invitacion",
                             help="anula una invitacion pendiente")
    rev_inv.add_argument("id", help="id o prefijo del id (el de `listar`)")
    rev_inv.set_defaults(funcion=cmd_revocar_invitacion)

    rev_acc = sub.add_parser("revocar-acceso", help="quita el acceso a alguien")
    rev_acc.add_argument("telegram_user_id", type=int)
    rev_acc.add_argument("--motivo", default=None)
    rev_acc.add_argument("--por", default=None)
    rev_acc.set_defaults(funcion=cmd_revocar_acceso)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return args.funcion(args)
    except SinCredenciales as exc:
        print(f"No se puede hablar con Supabase: {exc}")
        print("Pon SUPABASE_URL y SUPABASE_SERVICE_KEY en el entorno (o .env).")
        return 2
    except TablaAusente:
        print("La migracion 016 NO esta aplicada todavia: no existen todavia las")
        print("tablas `bot_allowlist` / `bot_invitaciones`.")
        print(f"Aplicala en el SQL editor de Supabase: {_MIGRACION}")
        print("(FASE A diagnostico -> FASE B aplicar -> FASE C validacion).")
        return 2
    except httpx.HTTPStatusError as exc:
        print(f"Supabase rechazo la peticion: HTTP {exc.response.status_code}")
        return 2
    except httpx.HTTPError as exc:
        print(f"No se pudo hablar con Supabase: {type(exc).__name__}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
