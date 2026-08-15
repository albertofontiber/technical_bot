#!/bin/bash
# Hook de arranque para Claude Code EN LA NUBE (s315c): deja el contenedor
# remoto listo para trabajar — dependencias, historial git completo y
# PYTHONPATH — sin los arreglos a mano que costó la primera sesión cloud (s315).
# En local no hace nada: el entorno de la máquina de Alberto ya está montado.
#
# s323: idempotente. El hook corre en CADA arranque Y en cada `resume` (la doc
# oficial lo declara como el coste de un SessionStart hook frente a un setup
# script, que sí se cachea), así que reinstalar siempre eran minutos regalados
# en cada reanudación. Ahora la instalación se salta cuando ya está hecha; el
# centinela combina la HUELLA de los requirements (si cambian, reinstala) con un
# import real (si la VM es nueva, el marcador no existe y reinstala igual).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# Indirección para poder verificar el flujo del hook sin instalar nada:
#   TB_PIP_CMD="echo [dry-run] pip" bash .claude/hooks/session-start.sh
PIP="${TB_PIP_CMD:-python3 -m pip install -q}"

# 1) Historial COMPLETO: el clon web es shallow y los tests de contratos
#    congelados (sha-pins s117/s196-s201/s277...) leen blobs de commits viejos
#    con `git cat-file` — sin esto fallan ~180 tests que en local están verdes.
if [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
  git fetch --unshallow -q || echo "AVISO: unshallow falló (¿sin red al remoto?)"
fi

# 2) Dependencias. Los tres arreglos vienen de la sesión s315 (cazados a mano):
#    - langdetect no compila su wheel en este contenedor → se instala el resto y
#      langdetect se tolera aparte (ningún módulo de src/scripts lo importa hoy);
#    - la cryptography del sistema (deb) hace PanicException con pyo3 → upgrade
#      forzado;
#    - pytest/pandas/etc. viven en requirements-dev.
#    OJO: requirements-dev.txt arrastra `-r requirements.txt` (langdetect volvería
#    a entrar por ahí) → se re-apunta al filtrado.
#    Los paquetes deb del sistema (PyJWT, cryptography) no tienen RECORD y pip no
#    puede desinstalarlos → se pisan por adelantado con --ignore-installed.
REQ_HUELLA="$(cat requirements.txt requirements-dev.txt | sha1sum | cut -d' ' -f1)"
MARCA="/tmp/.technical_bot_deps_${REQ_HUELLA}"

# El sondeo incluye `cryptography` A PROPÓSITO: es el módulo cuyo PanicException
# AL IMPORTAR (deb del sistema con pyo3) motivó este hook en s315 — un sondeo que
# no lo tocase daría por buena una VM rota. Misma razón para openai/voyageai: son
# críticos en scripts/cloud_smoke.py y el centinela debe coincidir con esa lista
# (hallazgo del revisor adversarial, s323).
if [ -f "$MARCA" ] && python3 -c "import pytest, jsonschema, pandas, httpx, anthropic, openai, voyageai, cryptography" 2>/dev/null; then
  echo "session-start: dependencias ya instaladas (${REQ_HUELLA:0:8}) — se salta la instalación"
else
  $PIP --ignore-installed PyJWT cryptography
  grep -v '^langdetect' requirements.txt > /tmp/req_sin_langdetect.txt
  sed 's|^-r requirements.txt|-r /tmp/req_sin_langdetect.txt|' requirements-dev.txt \
    > /tmp/req_dev_filtrado.txt
  $PIP -r /tmp/req_sin_langdetect.txt -r /tmp/req_dev_filtrado.txt
  $PIP langdetect || echo "AVISO: langdetect no instalado (tolerado)"
  $PIP pytest jsonschema pandas openpyxl \
    lingua-language-detector psycopg2-binary
  touch "$MARCA"
  echo "session-start: dependencias instaladas (${REQ_HUELLA:0:8})"
fi

# 3) La suite se corre con `PYTHONPATH=. python -m pytest` (convención del repo).
#    Fallback: con `set -u`, una CLAUDE_ENV_FILE ausente abortaría el hook DESPUÉS
#    de haber instalado — el trabajo hecho no debe perderse por eso.
echo 'export PYTHONPATH="."' >> "${CLAUDE_ENV_FILE:-/dev/null}"

echo "session-start: entorno web listo (deps + historial completo + PYTHONPATH)"
echo "session-start: verifica el entorno con \`python scripts/cloud_smoke.py\`"
