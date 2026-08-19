#!/usr/bin/env python3
"""Verificador del ENTORNO de una sesión — cloud o local (s323).

Por qué existe: el trabajo de este repo en una sesión cloud depende de cosas que
NO se ven hasta que fallan a mitad de camino — el historial git shallow (sin
`unshallow` fallan ~180 tests de contratos congelados), una dependencia que no
compiló, una API key ausente (s315/s316: `OPENAI_API_KEY` faltaba y el dúo del
Protocolo 3 quedó cojo SIN avisar) o la política de red bloqueando un portal
(casmarglobal en s315). Este script los comprueba TODOS de una vez, en el mismo
turno, y estampa un recibo — que es lo que el Protocolo 1 pide antes de declarar
que un entorno "funciona".

Se corre en la PRIMERA sesión de un entorno cloud nuevo, y cada vez que caduque
el caché del environment (~7 días) o se toque una variable.

NUNCA imprime el VALOR de un secreto: solo si está presente y su longitud. El
recibo es publicable (mismo contrato que scripts/s322_railway_censo.py).

Uso:
    python scripts/cloud_smoke.py                 # todo, con recibo en evals/
    python scripts/cloud_smoke.py --sin-red       # solo entorno, deps y keys
    python scripts/cloud_smoke.py --sin-recibo    # no escribe fichero
    python scripts/cloud_smoke.py --recibo RUTA   # recibo en otra ruta

Exit 0 si todo lo CRÍTICO pasa; 1 si algo crítico falla (los AVISO no rompen).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOTENV_CARGADO = False

OK, FALLO, AVISO, SKIP = "OK", "FALLO", "AVISO", "SKIP"


def cargar_dotenv() -> bool:
    """Mismo contrato que cualquier script del repo (src/config.py): el entorno
    del proceso manda y `.env` solo rellena huecos. En LOCAL eso hace que el
    smoke vea lo mismo que verá el trabajo real; en CLOUD no hay `.env` y todo
    sale del environment, que es justo lo que queremos comprobar.
    """
    try:
        from dotenv import load_dotenv

        return bool(load_dotenv(ROOT / ".env", override=False))
    except Exception:
        return False

# Secretos que el trabajo cloud necesita. `critico` = sin esto, la clase de
# trabajo que lo usa no se puede hacer en esa sesión.
SECRETOS = [
    ("SUPABASE_URL", True, "scripts contra la DB (harness, sondas, loaders)"),
    ("SUPABASE_SERVICE_KEY", True, "ídem — los SCRIPTS leen esto, no el MCP"),
    # En CLOUD la plataforma no inyecta esta variable (s325d): define
    # ANTHROPIC_API_KEY_SCRIPTS y el hook de arranque la reconstruye.
    ("ANTHROPIC_API_KEY", True, "generadores, harness, sondas, revisor Fable "
                                "— en cloud: define ANTHROPIC_API_KEY_SCRIPTS"),
    ("VOYAGE_API_KEY", True, "embeddings de chunks_v2 (retrieval real)"),
    ("OPENAI_API_KEY", True, "revisor Sol del dúo (Protocolo 3) y juez"),
    ("LLAMAPARSE_API_KEY", False, "LlamaParse — el nombre que exige ingest_new.py:319"),
    ("DATABASE_URL", False, "DDL y scripts de operador EN LOCAL (en cloud no hay TCP)"),
    ("RAILWAY_TOKEN", False, "censo de producción: flags y vars vivas (s322f)"),
    ("NOTIFIER_USER", False, "harvest del portal Notifier (con NOTIFIER_PASSWORD)"),
    ("NOTIFIER_PASSWORD", False, "harvest del portal Notifier (con NOTIFIER_USER)"),
]

# Módulos que deben IMPORTAR de verdad (no basta find_spec: el fallo de s315 era
# una `cryptography` del sistema que petaba con PanicException AL IMPORTAR).
MODULOS = [
    ("pytest", True),
    ("jsonschema", True),
    ("httpx", True),
    ("dotenv", True),
    ("anthropic", True),
    ("openai", True),
    ("voyageai", True),
    # Declarado en requirements.txt pero NO importado por src/ ni scripts/: el
    # acceso a la DB va por REST/httpx (src/logging_db.py). Si su import se
    # rompe, no bloquea trabajo — por eso no es crítico.
    ("supabase", False),
    ("cryptography", True),
    ("pandas", True),
    ("openpyxl", True),
    ("fitz", False),          # pymupdf — solo rutas de ingesta
    ("lingua", False),        # detector de idioma
    ("psycopg2", False),      # solo scripts que van por conexión directa
    ("langdetect", False),    # no compila en el contenedor web (tolerado, s315c)
]


def _sanear(texto: str) -> str:
    """Redacta cualquier valor de secreto que se haya colado en un detalle.

    Punto ÚNICO de saneado: todo detalle pasa por `_res`. Sin esto, el contrato
    de no-fuga dependía de que ningún mensaje de error arrastrase un valor — y
    los mensajes de httpx incluyen la URL, que lleva `SUPABASE_URL` dentro, y
    `r.text` de una respuesta de error puede devolver lo que se le envió
    (hallazgo del revisor adversarial, s323).
    """
    if not texto:
        return texto
    for nombre, _, _ in SECRETOS:
        valor = os.getenv(nombre, "")
        if len(valor) >= 8 and valor in texto:
            texto = texto.replace(valor, f"‹{nombre} REDACTADO›")
    # La password del DSN aparte: un error de psycopg2 puede citar trozos del DSN
    # sin citarlo entero, y entonces el reemplazo de arriba no engancha.
    clave = re.search(r"://[^:/@\s]+:([^@\s]+)@", os.getenv("DATABASE_URL", ""))
    if clave and len(clave.group(1)) >= 6 and clave.group(1) in texto:
        texto = texto.replace(clave.group(1), "‹DATABASE_URL:password REDACTADO›")
    return texto


def _sin_credencial(url: str) -> str:
    """Quita el `usuario:token@` de una URL.

    El recibo se COMMITEA, y en un clon cloud el remote puede venir como
    `https://x-access-token:<token>@github.com/...` — un secreto que no está en
    la lista de arriba porque lo inyecta el proxy, no el environment.
    """
    return re.sub(r"://[^/@\s]*@", "://", url)


def _res(nombre, estado, detalle, critico=True):
    return {
        "check": nombre,
        "estado": estado,
        "detalle": _sanear(detalle),
        "critico": critico,
    }


def _git(*args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=30
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def check_entorno():
    res = []
    remoto = os.getenv("CLAUDE_CODE_REMOTE", "") == "true"
    res.append(
        _res(
            "superficie",
            OK,
            f"{'sesión CLOUD' if remoto else 'sesión LOCAL'} · "
            f"{platform.system()} {platform.machine()} · python {platform.python_version()}",
            critico=False,
        )
    )

    # Enlace de vuelta a la sesión que produjo el recibo (trazabilidad).
    sid = os.getenv("CLAUDE_CODE_REMOTE_SESSION_ID", "")
    if sid:
        url = "https://claude.ai/code/" + (
            sid.replace("cse_", "session_", 1) if sid.startswith("cse_") else sid
        )
        res.append(_res("sesion_url", OK, url, critico=False))

    # PYTHONPATH=. es la convención del repo; el hook lo escribe en cloud.
    py = os.getenv("PYTHONPATH", "")
    res.append(
        _res(
            "PYTHONPATH",
            OK if py else AVISO,
            py or "vacío — usa `PYTHONPATH=. python -m pytest` o el hook no corrió",
            critico=False,
        )
    )
    return res


def check_repo():
    res = []
    shallow = _git("rev-parse", "--is-shallow-repository") == "true"
    res.append(
        _res(
            "git_historial_completo",
            FALLO if shallow else OK,
            "SHALLOW — los tests de contratos congelados leen blobs viejos con "
            "`git cat-file`; sin `git fetch --unshallow` fallan ~180 (s315c)"
            if shallow
            else "completo (no shallow)",
        )
    )
    rama = _git("rev-parse", "--abbrev-ref", "HEAD") or "?"
    sha = _git("rev-parse", "--short", "HEAD") or "?"
    res.append(_res("git_head", OK, f"{rama} @ {sha}", critico=False))
    res.append(
        _res(
            "git_origin",
            OK,
            _sin_credencial(_git("remote", "get-url", "origin") or "?"),
            critico=False,
        )
    )
    return res


def check_modulos():
    res = []
    for mod, critico in MODULOS:
        try:
            __import__(mod)
            res.append(_res(f"import:{mod}", OK, "importa", critico=critico))
        except BaseException as exc:  # BaseException: pyo3 lanza PanicException
            res.append(
                _res(
                    f"import:{mod}",
                    FALLO if critico else AVISO,
                    f"{type(exc).__name__}: {exc}"[:200],
                    critico=critico,
                )
            )
    return res


def check_deps_cache():
    """s325g: ¿la caché del environment trajo las deps pre-instaladas?

    El setup script deja un marcador en site-packages (install-deps.sh); sin esta
    línea en el recibo, un setup que NUNCA funciona sería invisible — el hook lo
    taparía instalando en silencio cada VM (hallazgo del revisor adversarial,
    s325g). La EDAD del marcador es la señal: días = vino del snapshot; minutos =
    lo acaba de estampar el hook en este arranque, la caché no lo trajo.
    Informativo a propósito: su ausencia o edad no rompe nada (el hook cubre).
    """
    if os.getenv("CLAUDE_CODE_REMOTE", "") != "true":
        return [_res("deps_cache", SKIP, "solo aplica a sesiones cloud", critico=False)]
    try:
        import hashlib
        import sysconfig
        import time

        # MISMA receta que install-deps.sh (requirements + requirements-dev + el
        # PROPIO script — la huella cambió en s325g-r2 para que un cambio del
        # script invalide el marcador). Si esto y el shell divergen, esta línea
        # reportará «sin marcador para la huella actual» con el marcador presente
        # — esa asimetría ES el detector de la divergencia.
        huella = hashlib.sha1(
            (ROOT / "requirements.txt").read_bytes()
            + (ROOT / "requirements-dev.txt").read_bytes()
            + (ROOT / ".claude" / "hooks" / "install-deps.sh").read_bytes()
        ).hexdigest()
        purelib = Path(sysconfig.get_paths()["purelib"])
        marca = purelib / f".technical_bot_deps_{huella}"
        if marca.exists():
            # Atribución por el ARRANQUE de la VM, no por umbral de edad (Fable r2):
            # mtime anterior al boot solo puede venir del snapshot restaurado. Asume
            # /proc/uptime de la VM (medido cierto en s325g) y restore previo al
            # instante medido de boot — ambos declarados en DEC-235, no garantizados.
            mtime = marca.stat().st_mtime
            arranque_vm = time.time() - float(Path("/proc/uptime").read_text().split()[0])
            edad_min = (time.time() - mtime) / 60
            origen = (
                f"anterior a esta VM (edad {edad_min / 1440:.1f} días) — vino del snapshot"
                if mtime < arranque_vm
                else f"estampado en esta VM hace {edad_min:.0f} min — build del snapshot o "
                "fallback del hook (la caché no lo traía)"
            )
            return [_res("deps_cache", OK, f"marcador {huella[:8]} · {origen}", critico=False)]
        otras = len(list(purelib.glob(".technical_bot_deps_*")))
        return [
            _res(
                "deps_cache",
                OK,
                f"sin marcador para la huella actual ({huella[:8]})"
                + (
                    f"; hay {otras} de otra huella — los requirements cambiaron tras el snapshot"
                    if otras
                    else " — caché fría o setup script sin configurar (el hook instala)"
                ),
                critico=False,
            )
        ]
    except Exception as exc:
        return [_res("deps_cache", AVISO, f"{type(exc).__name__}: {exc}"[:200], critico=False)]


def check_secretos():
    res = []
    for nombre, critico, para_que in SECRETOS:
        valor = os.getenv(nombre, "")
        res.append(
            _res(
                f"key:{nombre}",
                OK if valor else (FALLO if critico else AVISO),
                f"presente ({len(valor)} chars) — {para_que}"
                if valor
                else f"AUSENTE — {para_que}",
                critico=critico,
            )
        )

    # El bot vive en Railway: un token suelto en una sesión CLOUD haría polling
    # COMPITIENDO con producción (roba updates de Telegram a los técnicos). En
    # local el token está en `.env` a propósito (se puede correr el bot), así
    # que la regla solo aplica al environment cloud.
    if os.getenv("TELEGRAM_BOT_TOKEN", "") and os.getenv("CLAUDE_CODE_REMOTE") == "true":
        res.append(
            _res(
                "key:TELEGRAM_BOT_TOKEN",
                AVISO,
                "PRESENTE y no debería: el bot vive en Railway; un script con "
                "polling aquí compite con producción. Quítalo del environment.",
                critico=False,
            )
        )
    return res


def check_red():
    """Conectividad REAL por servicio. Todas las llamadas son de coste ~0."""
    res = []
    try:
        import httpx
    except Exception as exc:
        return [_res("red", FALLO, f"httpx no importable: {exc}")]

    def _get(nombre, url, headers, critico=True, metodo="GET", json_body=None):
        try:
            r = httpx.request(
                metodo, url, headers=headers, json=json_body, timeout=30.0
            )
            ok = r.status_code < 400
            return _res(
                nombre,
                OK if ok else FALLO,
                f"HTTP {r.status_code}"
                + ("" if ok else f" · {r.text[:160]}"),
                critico=critico,
            )
        except Exception as exc:
            return _res(nombre, FALLO, f"{type(exc).__name__}: {exc}"[:200], critico=critico)

    sb_url, sb_key = os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_SERVICE_KEY", "")
    if sb_url and sb_key:
        res.append(
            _get(
                "red:supabase",
                f"{sb_url.rstrip('/')}/rest/v1/documents?select=id&limit=1",
                {"apikey": sb_key, "Authorization": f"Bearer {sb_key}"},
            )
        )
    else:
        res.append(_res("red:supabase", SKIP, "sin SUPABASE_URL/SERVICE_KEY", critico=True))

    if os.getenv("ANTHROPIC_API_KEY"):
        res.append(
            _get(
                "red:anthropic",
                "https://api.anthropic.com/v1/models?limit=1",
                {
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                },
            )
        )
    else:
        res.append(_res("red:anthropic", SKIP, "sin ANTHROPIC_API_KEY", critico=True))

    if os.getenv("OPENAI_API_KEY"):
        res.append(
            _get(
                "red:openai",
                "https://api.openai.com/v1/models",
                {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            )
        )
    else:
        res.append(
            _res(
                "red:openai",
                SKIP,
                "sin OPENAI_API_KEY — el revisor Sol del Protocolo 3 NO es "
                "ejecutable en esta sesión (s316: el dúo quedó cojo así)",
                critico=True,
            )
        )

    # Voyage no tiene endpoint gratuito: un embed de 1 token cuesta ~0 y además
    # verifica la DIMENSIÓN que el corpus chunks_v2 espera (1024).
    if os.getenv("VOYAGE_API_KEY"):
        modelo = os.getenv("EMBED_MODEL", "voyage-4-large")
        r = _get(
            "red:voyage",
            "https://api.voyageai.com/v1/embeddings",
            {"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"},
            metodo="POST",
            json_body={"model": modelo, "input": ["ping"], "output_dimension": 1024},
        )
        res.append(r)
    else:
        res.append(_res("red:voyage", SKIP, "sin VOYAGE_API_KEY", critico=True))

    # Conexión DIRECTA a Postgres: es lo que hace falta para DDL/migraciones y
    # para los scripts de operador (rgpd_retencion, marcar_utilidad). Opcional: sin
    # DATABASE_URL la sesión puede leer y escribir DATOS por REST igualmente.
    # Nota: el DSN del repo apunta al POOLER (aws-N-<region>.pooler.supabase.com),
    # que resuelve por IPv4 — la conexión directa `db.<ref>.supabase.co` es IPv6 y
    # no está garantizada desde el VM.
    dsn = os.getenv("DATABASE_URL", "")
    if dsn:
        conexion = None
        try:
            import psycopg2

            conexion = psycopg2.connect(dsn, connect_timeout=15)
            with conexion.cursor() as cur:
                cur.execute("select 1")
                cur.fetchone()
            res.append(
                _res("red:postgres", OK, "conexión directa OK — DDL posible", critico=False)
            )
        except Exception as exc:
            # En CLOUD esto es lo ESPERADO, no un environment mal montado: el proxy
            # de la sesion deja pasar HTTP/HTTPS y no TCP arbitrario, asi que el 5432
            # da timeout aunque la red este en Full (medido en s325d). Las
            # migraciones desde cloud van por el conector MCP de Supabase.
            nota = (" — ESPERADO en cloud: el proxy no permite TCP al 5432; para DDL "
                    "usa el conector MCP de Supabase"
                    if os.getenv("CLAUDE_CODE_REMOTE") == "true" else "")
            res.append(
                _res("red:postgres", FALLO,
                     f"{type(exc).__name__}: {exc}"[:200] + nota, critico=False)
            )
        finally:
            if conexion is not None:
                conexion.close()
    else:
        res.append(
            _res(
                "red:postgres",
                SKIP,
                "sin DATABASE_URL — esta sesión no puede aplicar migraciones por "
                "conexión directa (los DATOS por REST sí funcionan)",
                critico=False,
            )
        )

    # Extraction store (s325b): ¿puede ESTA sesión leer las extracciones? Se pregunta
    # al bucket a propósito (`directorio=None`), que es lo que verá una sesión cloud.
    # No es crítico: evals, código y docs no lo necesitan; enunciados y re-ingesta sí.
    try:
        from src.extraction_store import abrir_store

        st = abrir_store()
        res.append(
            _res("red:extraction_store", OK,
                 f"{st.origen}: {len(st.listar())} extracciones", critico=False)
        )
    except Exception as exc:
        res.append(
            _res("red:extraction_store", FALLO,
                 f"{type(exc).__name__}: {exc}"[:200], critico=False)
        )

    # Portal de fabricante: prueba la POLÍTICA DE RED del environment, no una
    # key. Con Trusted esto se bloquea (s315); con Full o Custom-con-el-dominio
    # pasa. No es crítico: solo el harvest lo necesita.
    res.append(
        _get(
            "red:portal_fabricante",
            "https://www.casmarglobal.com/",
            {"User-Agent": "technical-bot-cloud-smoke/1.0"},
            critico=False,
        )
    )
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica el entorno de la sesión (cloud o local)")
    ap.add_argument("--sin-red", action="store_true", help="salta la conectividad")
    ap.add_argument("--sin-recibo", action="store_true", help="no escribe el recibo")
    ap.add_argument(
        "--sin-dotenv",
        action="store_true",
        help="ignora el .env local (simula desde local lo que vería una sesión cloud)",
    )
    ap.add_argument(
        "--recibo",
        default=str(ROOT / "evals" / "s323_cloud_smoke_v1.json"),
        help="ruta del recibo JSON",
    )
    args = ap.parse_args()

    global DOTENV_CARGADO
    DOTENV_CARGADO = False if args.sin_dotenv else cargar_dotenv()

    resultados = []
    resultados += check_entorno()
    resultados += check_repo()
    resultados += check_modulos()
    resultados += check_deps_cache()
    resultados += check_secretos()
    resultados += [] if args.sin_red else check_red()

    ancho = max(len(r["check"]) for r in resultados)
    print()
    for r in resultados:
        marca = {OK: "  OK  ", FALLO: " FALLO", AVISO: " AVISO", SKIP: " SKIP "}[r["estado"]]
        print(f"[{marca}] {r['check']:<{ancho}}  {r['detalle']}")

    criticos = [r for r in resultados if r["critico"] and r["estado"] in (FALLO, SKIP)]
    avisos = [r for r in resultados if r["estado"] == AVISO]
    veredicto = "LISTO" if not criticos else "NO LISTO"

    print()
    print(f"VEREDICTO: {veredicto} · {len(criticos)} crítico(s) en fallo · {len(avisos)} aviso(s)")
    for r in criticos:
        print(f"  ✗ {r['check']}: {r['detalle']}")

    if not args.sin_recibo:
        recibo = {
            "generado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "veredicto": veredicto,
            "superficie": "cloud" if os.getenv("CLAUDE_CODE_REMOTE") == "true" else "local",
            "dotenv_cargado": DOTENV_CARGADO,
            "red_comprobada": not args.sin_red,
            "checks": resultados,
        }
        destino = Path(args.recibo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(recibo, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRecibo: {destino.relative_to(ROOT) if destino.is_relative_to(ROOT) else destino}")

    return 0 if not criticos else 1


if __name__ == "__main__":
    sys.exit(main())
