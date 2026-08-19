"""Contratos de `scripts/cloud_smoke.py` (s323).

El script existe para verificar entornos de sesión y por definición TOCA todos
los secretos del proyecto. Su contrato central es que jamás vuelca un valor —
ni por pantalla ni en el recibo, que se commitea a `evals/`. Eso no puede
quedarse en una promesa del docstring: aquí se fija como test.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "cloud_smoke.py"

# Valores falsos, largos y distintivos: si alguno aparece en la salida o en el
# recibo, hay fuga.
SECRETOS_FALSOS = {
    "SUPABASE_URL": "https://fuga-supabase-url.example.invalid",
    "SUPABASE_SERVICE_KEY": "FUGA_SERVICE_KEY_ZZQQ_9f3b7d1e5a2c4b6d8e0f",
    "ANTHROPIC_API_KEY": "FUGA_ANTHROPIC_KEY_ZZQQ_1a2b3c4d5e6f7a8b9c0d",
    "VOYAGE_API_KEY": "FUGA_VOYAGE_KEY_ZZQQ_0f9e8d7c6b5a4938271605",
    "OPENAI_API_KEY": "FUGA_OPENAI_KEY_ZZQQ_abcdef0123456789abcdef",
    "LLAMA_CLOUD_API_KEY": "FUGA_LLAMA_KEY_ZZQQ_5544332211009988776655",
    "TELEGRAM_BOT_TOKEN": "FUGA_TELEGRAM_TOKEN_ZZQQ_1234567890:AAaaBBbb",
}


def _correr(env_extra, recibo: Path, args=()):
    # PYTHONIOENCODING + encoding explícito: en Windows la consola decodifica en
    # cp1252 y los acentos de la salida llegarían como mojibake al test.
    # CLAUDE_CODE_REMOTE se limpia del entorno HEREDADO y solo entra si el test lo
    # pide: corriendo la suite DENTRO de una sesion cloud, el subproceso la heredaba
    # y el caso "local" veia superficie=cloud (fallo real, cazado por el smoke de
    # recepcion de s325d — el unico sitio donde podia aparecer).
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_REMOTE"}
    env.update({"PYTHONIOENCODING": "utf-8", **env_extra})
    # `--sin-dotenv` para que el `.env` local no contamine el entorno bajo test.
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--sin-red", "--sin-dotenv",
         "--recibo", str(recibo), *args],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=300,
    )
    return proc


def test_no_vuelca_ningun_secreto_en_salida_ni_recibo(tmp_path) -> None:
    recibo = tmp_path / "recibo.json"
    proc = _correr(SECRETOS_FALSOS, recibo)

    texto_recibo = recibo.read_text(encoding="utf-8")
    for nombre, valor in SECRETOS_FALSOS.items():
        assert valor not in proc.stdout, f"{nombre} volcado por pantalla"
        assert valor not in proc.stderr, f"{nombre} volcado a stderr"
        assert valor not in texto_recibo, f"{nombre} volcado al recibo"


def test_reporta_presencia_y_longitud_sin_el_valor(tmp_path) -> None:
    recibo = tmp_path / "recibo.json"
    proc = _correr(SECRETOS_FALSOS, recibo)

    largo = len(SECRETOS_FALSOS["ANTHROPIC_API_KEY"])
    assert f"presente ({largo} chars)" in proc.stdout
    assert proc.returncode == 0, "con todas las keys presentes el veredicto es LISTO"

    datos = json.loads(recibo.read_text(encoding="utf-8"))
    assert datos["veredicto"] == "LISTO"
    assert datos["dotenv_cargado"] is False
    assert datos["red_comprobada"] is False


def test_key_critica_ausente_rompe_el_veredicto(tmp_path) -> None:
    recibo = tmp_path / "recibo.json"
    sin_sol = {**SECRETOS_FALSOS, "OPENAI_API_KEY": ""}
    proc = _correr(sin_sol, recibo)

    assert proc.returncode == 1, "sin OPENAI_API_KEY el dúo del Protocolo 3 queda cojo"
    datos = json.loads(recibo.read_text(encoding="utf-8"))
    assert datos["veredicto"] == "NO LISTO"
    fallo = [c for c in datos["checks"] if c["check"] == "key:OPENAI_API_KEY"][0]
    assert fallo["estado"] == "FALLO"


def _sin_fugas(objeto) -> None:
    texto = json.dumps(objeto, ensure_ascii=False)
    for nombre, valor in SECRETOS_FALSOS.items():
        assert valor not in texto, f"{nombre} filtrado en {texto[:300]}"


def test_check_red_no_filtra_secretos_en_excepciones(monkeypatch) -> None:
    """La excepción de httpx incluye la URL — y la URL lleva SUPABASE_URL."""
    import httpx

    from scripts import cloud_smoke

    for nombre, valor in SECRETOS_FALSOS.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.delenv("DATABASE_URL", raising=False)  # el check de DDL, a SKIP

    def _peta(metodo, url, **kwargs):
        raise httpx.ConnectError(
            f"no se pudo conectar a {url} "
            f"(auth {SECRETOS_FALSOS['SUPABASE_SERVICE_KEY']})"
        )

    monkeypatch.setattr(httpx, "request", _peta)
    _sin_fugas(cloud_smoke.check_red())


def test_check_red_no_filtra_secretos_en_respuestas_de_error(monkeypatch) -> None:
    """`r.text` de un 4xx puede devolver lo que se le envió."""
    import httpx

    from scripts import cloud_smoke

    for nombre, valor in SECRETOS_FALSOS.items():
        monkeypatch.setenv(nombre, valor)
    monkeypatch.delenv("DATABASE_URL", raising=False)  # el check de DDL, a SKIP

    def _cuatrocientos(metodo, url, **kwargs):
        return httpx.Response(
            401,
            text=f"invalid key {SECRETOS_FALSOS['OPENAI_API_KEY']} for {url}",
            request=httpx.Request(metodo, "https://ejemplo.invalid"),
        )

    monkeypatch.setattr(httpx, "request", _cuatrocientos)
    _sin_fugas(cloud_smoke.check_red())


def test_el_recibo_no_publica_credenciales_del_remote(monkeypatch) -> None:
    """El recibo se COMMITEA: un remote con token embebido no puede acabar ahí."""
    from scripts import cloud_smoke

    monkeypatch.setattr(
        cloud_smoke,
        "_git",
        lambda *args: (
            "https://x-access-token:ghs_FUGA_TOKEN_ZZQQ@github.com/albertofontiber/technical_bot.git"
            if args[0] == "remote"
            else "valor"
        ),
    )
    origen = [c for c in cloud_smoke.check_repo() if c["check"] == "git_origin"][0]
    assert "ghs_FUGA_TOKEN_ZZQQ" not in origen["detalle"]
    assert origen["detalle"].startswith("https://github.com/")


def test_aviso_de_telegram_solo_en_sesiones_cloud(tmp_path) -> None:
    # En local el token vive en `.env` a propósito (se puede correr el bot).
    local = _correr(SECRETOS_FALSOS, tmp_path / "local.json")
    assert "PRESENTE y no debería" not in local.stdout

    # En cloud, un polling suelto competiría con el bot de producción.
    cloud = _correr(
        {**SECRETOS_FALSOS, "CLAUDE_CODE_REMOTE": "true"}, tmp_path / "cloud.json"
    )
    assert "PRESENTE y no debería" in cloud.stdout
    datos = json.loads((tmp_path / "cloud.json").read_text(encoding="utf-8"))
    assert datos["superficie"] == "cloud"


# ---------------------------------------------------------------- s325h ------
# El check `deps_cache` dejó de INFERIR el origen por mtime-vs-/proc/uptime (un
# reinicio del contenedor reseteaba el uptime y un marcador nacido en la propia VM
# se declaraba «vino del snapshot» — falso, medido en s325h) y pasó a LEER el
# registro que install-deps.sh apendiza en cada corrida, sellado con el boot_id.
# /proc solo existe en Linux, y este fichero declara Windows como superficie de
# desarrollo (ver el comentario de PYTHONIOENCODING arriba). Sin esta guarda, los
# tests del registro fallarían allí por el entorno, no por el contrato (Fable r2).
sin_proc = pytest.mark.skipif(
    not Path("/proc/sys/kernel/random/boot_id").exists(),
    reason="el registro por arranque se sella con /proc (solo Linux)",
)


def _boot_uptime():
    return (
        Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        float(Path("/proc/uptime").read_text().split()[0]),
    )


def _huella_actual():
    import hashlib

    from scripts import cloud_smoke

    raiz = cloud_smoke.ROOT
    return hashlib.sha1(
        (raiz / "requirements.txt").read_bytes()
        + (raiz / "requirements-dev.txt").read_bytes()
        + (raiz / ".claude" / "hooks" / "install-deps.sh").read_bytes()
    ).hexdigest()[:8]


def _deps_cache(tmp_path, lineas_registro, con_marcador=True, monkeypatch=None):
    """Corre check_deps_cache con un registro y un marcador controlados."""
    import hashlib
    import sysconfig

    from scripts import cloud_smoke

    registro = tmp_path / "registro"
    if lineas_registro is not None:
        registro.write_text("\n".join(lineas_registro) + "\n", encoding="utf-8")

    raiz = cloud_smoke.ROOT
    huella = hashlib.sha1(
        (raiz / "requirements.txt").read_bytes()
        + (raiz / "requirements-dev.txt").read_bytes()
        + (raiz / ".claude" / "hooks" / "install-deps.sh").read_bytes()
    ).hexdigest()
    marca = Path(sysconfig.get_paths()["purelib"]) / f".technical_bot_deps_{huella}"
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.setenv("TB_REGISTRO", str(registro))
    return cloud_smoke.check_deps_cache()[0], marca.exists(), huella


@sin_proc
def test_deps_cache_dice_la_verdad_cuando_se_instalo_en_este_arranque(tmp_path, monkeypatch):
    """El caso que la versión vieja disfrazaba de «vino del snapshot»."""
    boot, up = _boot_uptime()
    h = _huella_actual()
    res, _, _ = _deps_cache(
        tmp_path,
        [f"instalada {h} {boot} {up - 60:.2f} 2026-08-19T14:14:12Z",
         f"saltada {h} {boot} {up - 30:.2f} 2026-08-19T14:14:20Z"],
        monkeypatch=monkeypatch,
    )
    assert "INSTALADAS en este arranque" in res["detalle"]
    assert "no las traía" in res["detalle"]
    assert res["critico"] is False


@sin_proc
def test_deps_cache_reconoce_el_ahorro_solo_si_nadie_instalo(tmp_path, monkeypatch):
    boot, up = _boot_uptime()
    h = _huella_actual()
    res, _, _ = _deps_cache(
        tmp_path, [f"saltada {h} {boot} {up - 10:.2f} 2026-08-19T15:00:00Z"],
        monkeypatch=monkeypatch,
    )
    assert "ya estaban al arrancar" in res["detalle"]
    assert "las trajo hechas" in res["detalle"]


@sin_proc
def test_deps_cache_ignora_lineas_de_OTRO_arranque(tmp_path, monkeypatch):
    """El corazón del arreglo: un registro heredado (otro boot_id) no cuenta —
    antes, tras un reinicio, esas líneas se atribuían a esta VM."""
    h = _huella_actual()
    res, _, _ = _deps_cache(
        tmp_path,
        [f"instalada {h} 00000000-1111-2222-3333-444444444444 5.0 2026-08-19T13:48:56Z"],
        monkeypatch=monkeypatch,
    )
    assert "sin registro de este arranque" in res["detalle"]
    assert res["estado"] == "AVISO", "sin evidencia no se afirma un origen"


@sin_proc
def test_deps_cache_ignora_lineas_de_OTRA_huella(tmp_path, monkeypatch):
    """Fable r2: si el instalador cambia a mitad de sesión (663fae88→e28aecda),
    las líneas de la receta vieja describen OTRA instalación."""
    boot, up = _boot_uptime()
    res, _, _ = _deps_cache(
        tmp_path, [f"instalada 663fae88 {boot} {up - 5:.2f} 2026-08-19T13:48:56Z"],
        monkeypatch=monkeypatch,
    )
    assert "sin registro de este arranque" in res["detalle"]
    assert res["estado"] == "AVISO"


@sin_proc
def test_deps_cache_descarta_uptime_imposible(tmp_path, monkeypatch):
    """Segundo sello: dentro de un arranque el uptime solo crece, así que una
    línea con uptime mayor que el actual viene de otro (boot_id reutilizado)."""
    boot, up = _boot_uptime()
    h = _huella_actual()
    res, _, _ = _deps_cache(
        tmp_path, [f"instalada {h} {boot} {up + 9999:.2f} 2026-08-19T13:00:00Z"],
        monkeypatch=monkeypatch,
    )
    assert res["estado"] == "AVISO"


@sin_proc
def test_deps_cache_no_inventa_origen_sin_registro(tmp_path, monkeypatch):
    res, _, _ = _deps_cache(tmp_path, None, monkeypatch=monkeypatch)
    assert "snapshot" not in res["detalle"].lower(), "no se afirma lo que no se puede probar"
    assert res["estado"] == "AVISO"


def test_deps_cache_solo_aplica_a_cloud(tmp_path, monkeypatch):
    from scripts import cloud_smoke

    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    assert cloud_smoke.check_deps_cache()[0]["estado"] == "SKIP"
