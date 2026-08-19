#!/bin/bash
# Hook de arranque para Claude Code EN LA NUBE (s315c): deja el contenedor
# remoto listo para trabajar — dependencias, historial git completo y
# PYTHONPATH — sin los arreglos a mano que costó la primera sesión cloud (s315).
# En local no hace nada: el entorno de la máquina de Alberto ya está montado.
#
# s323: idempotente — un `resume` no reinstala (centinela huella+import).
# s325g: la INSTALACIÓN vive en install-deps.sh, compartida con el setup script
# del environment, que la deja cacheada en el snapshot (~7 días). Aquí queda como
# FALLBACK autosanador: caché con las deps → no-op de ~3 s (medido); caché caducada, setup
# que no corrió, o requirements cambiados tras el snapshot → instala como siempre.
# Peor caso = el comportamiento de hoy para todo módulo del sondeo (críticos del
# smoke al completo); el residuo que el sondeo no ve queda declarado en DEC-235.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# 1) Historial COMPLETO: el clon web es shallow y los tests de contratos
#    congelados (sha-pins s117/s196-s201/s277...) leen blobs de commits viejos
#    con `git cat-file` — sin esto fallan ~180 tests que en local están verdes.
#    Se queda en el hook (no en el setup): el clon es POR SESIÓN, no del snapshot.
if [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
  git fetch --unshallow -q || echo "AVISO: unshallow falló (¿sin red al remoto?)"
fi

# 2) Dependencias (dry-run: TB_PIP_CMD/TB_MARCA_DIR — ver install-deps.sh).
bash "$CLAUDE_PROJECT_DIR/.claude/hooks/install-deps.sh"

# 3) La suite se corre con `PYTHONPATH=. python -m pytest` (convención del repo).
#    Fallback: con `set -u`, una CLAUDE_ENV_FILE ausente abortaría el hook DESPUÉS
#    de haber instalado — el trabajo hecho no debe perderse por eso.
echo 'export PYTHONPATH="."' >> "${CLAUDE_ENV_FILE:-/dev/null}"

# 4) La key de Anthropic para los SCRIPTS (s325f). La plataforma NO inyecta
#    `ANTHROPIC_API_KEY` en el contenedor —la UI avisa de que no autentica la sesion,
#    y el smoke de recepcion s325d confirmo que la sesion no la ve— pero el harness,
#    las sondas, los generadores y el revisor Fable la necesitan para llamar a la API.
#    Salida: define `ANTHROPIC_API_KEY_SCRIPTS` en el environment y aqui se reconstruye.
#    printf %q escapa el valor: una key con caracteres de shell romperia el env file.
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -n "${ANTHROPIC_API_KEY_SCRIPTS:-}" ]; then
  printf 'export ANTHROPIC_API_KEY=%q
' "$ANTHROPIC_API_KEY_SCRIPTS"     >> "${CLAUDE_ENV_FILE:-/dev/null}"
  echo "session-start: ANTHROPIC_API_KEY derivada de ANTHROPIC_API_KEY_SCRIPTS"
fi

echo "session-start: entorno web listo (deps + historial completo + PYTHONPATH)"
echo "session-start: verifica el entorno con \`python scripts/cloud_smoke.py\`"
