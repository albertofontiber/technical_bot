#!/bin/bash
# Hook de arranque para Claude Code EN LA WEB (s315c): deja el contenedor remoto
# listo para trabajar — dependencias, historial git completo y PYTHONPATH — sin
# los arreglos a mano que costó la primera sesión cloud (s315). En local no hace
# nada: el entorno de la máquina de Alberto ya está montado.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

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
python3 -m pip install -q --ignore-installed PyJWT cryptography
grep -v '^langdetect' requirements.txt > /tmp/req_sin_langdetect.txt
sed 's|^-r requirements.txt|-r /tmp/req_sin_langdetect.txt|' requirements-dev.txt \
  > /tmp/req_dev_filtrado.txt
python3 -m pip install -q -r /tmp/req_sin_langdetect.txt -r /tmp/req_dev_filtrado.txt
python3 -m pip install -q langdetect || echo "AVISO: langdetect no instalado (tolerado)"
python3 -m pip install -q pytest jsonschema pandas openpyxl \
  lingua-language-detector psycopg2-binary

# 3) La suite se corre con `PYTHONPATH=. python -m pytest` (convención del repo).
echo 'export PYTHONPATH="."' >> "$CLAUDE_ENV_FILE"

echo "session-start: entorno web listo (deps + historial completo + PYTHONPATH)"
