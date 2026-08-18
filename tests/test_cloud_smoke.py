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
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **env_extra}
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
