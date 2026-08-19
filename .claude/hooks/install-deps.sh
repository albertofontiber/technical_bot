#!/bin/bash
# Instalador de dependencias del contenedor cloud — LÓGICA ÚNICA con dos llamadores
# (s325g): el setup script del environment (corre solo al construir la caché y deja
# el resultado en el snapshot ~7 días) y el hook de SessionStart (fallback en cada
# arranque). Un solo fichero versionado para que el campo del environment no
# duplique lógica — la objeción registrada contra este movimiento (ENTORNO_CLOUD
# §3.6, s325d) era exactamente esa duplicación.
#
# Idempotente (s323): centinela = huella sha1 de los requirements + import real.
# s325g: el centinela se muda de /tmp a site-packages. La caché del environment es
# un snapshot del FILESYSTEM y /tmp puede ser tmpfs: un marcador que no viajara con
# los paquetes haría reinstalar en cada VM nueva aunque el snapshot trajera todo.
# En site-packages, marcador y paquetes viven y mueren JUNTOS por construcción
# (cambia el python del contenedor → cambia purelib → desaparecen ambos → reinstala).
#
# Los tres arreglos de s315 (cazados a mano):
#   - langdetect no compila su wheel en este contenedor → el resto primero y
#     langdetect tolerado aparte (ningún módulo de src/scripts lo importa hoy);
#   - la cryptography del sistema (deb) hace PanicException con pyo3 → se pisa por
#     adelantado con --ignore-installed (los deb no tienen RECORD y pip no puede
#     desinstalarlos; ídem PyJWT);
#   - requirements-dev.txt arrastra `-r requirements.txt` (langdetect volvería a
#     entrar por ahí) → se re-apunta al filtrado.
set -euo pipefail
SELF="$(readlink -f "$0")"   # antes del cd: $0 puede ser relativo
cd "$(dirname "$SELF")/../.."   # el script vive en .claude/hooks/ → raíz del repo

# Indirecciones para verificar el flujo sin instalar nada ni tocar el marcador real:
#   TB_PIP_CMD="echo [dry-run] pip" TB_MARCA_DIR=/tmp/prueba bash .claude/hooks/install-deps.sh
PIP="${TB_PIP_CMD:-python3 -m pip install -q}"
MARCA_DIR="${TB_MARCA_DIR:-$(python3 -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')}"

# La huella incluye EL PROPIO SCRIPT (hallazgo Fable r2): instala paquetes que no
# están en requirements y encapsula los workarounds s315 — sin esto, un cambio del
# script sin tocar requirements dejaría el marcador del snapshot válido y el cambio
# no se aplicaría en ninguna VM durante ~7 días (pre-s325g sí se aplicaba: el
# marcador moría con cada VM).
REQ_HUELLA="$(cat requirements.txt requirements-dev.txt "$SELF" | sha1sum | cut -d' ' -f1)"
MARCA="${MARCA_DIR}/.technical_bot_deps_${REQ_HUELLA}"

# REGISTRO de lo que se hace en CADA ejecución (s325h). Nace porque la atribución
# del smoke por mtime-vs-/proc/uptime dio un FALSO «vino del snapshot»: un reinicio
# del contenedor resetea el uptime y un marcador nacido en esa misma VM pasa por
# heredado (medido en s325h, VM 13:47→14:02). El registro sustituye la INFERENCIA
# por el HECHO: cada corrida apendiza «acción huella boot_id», y el `boot_id` del
# kernel (único por arranque, cambia en un reinicio) permite al smoke saber qué
# líneas son de ESTE arranque y cuáles de otro. Se apendiza —no se sobrescribe—
# porque en un mismo arranque corren DOS llamadores (setup script y hook): si el
# segundo pisara al primero, «el setup instaló» se perdería y el ahorro parecería
# real cuando no lo fue.
REGISTRO="${TB_REGISTRO:-/tmp/.technical_bot_deps_registro}"
BOOT_ID="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo desconocido)"

# El UPTIME acompaña al boot_id (Fable r2): si el runtime reutilizara el boot_id
# —contenedor sin kernel propio, o restore con memoria— una línea heredada tendría
# un uptime MAYOR que el actual, cosa imposible dentro de un mismo arranque porque
# el uptime solo crece. Es un segundo sello barato sobre un supuesto que NO está
# medido en este runtime (declarado en DEC-238 addendum).
anotar() {  # $1 = saltada | instalada
  printf '%s %s %s %s %s\n' "$1" "${REQ_HUELLA:0:8}" "$BOOT_ID" \
    "$(cut -d' ' -f1 /proc/uptime 2>/dev/null || echo 0)" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$REGISTRO" 2>/dev/null || true
}

# El sondeo incluye `cryptography` A PROPÓSITO: su PanicException de s315 salta AL
# IMPORTAR, y un sondeo que no lo tocase daría por buena una VM rota. La lista es
# TODOS los módulos críticos de scripts/cloud_smoke.py (contrato s323, completado
# en s325g: faltaban dotenv y openpyxl) — importa más ahora que un falso salto no
# muere con la VM sino que viaja en el snapshot ~7 días (hallazgo Fable s325g):
# cualquier crítico roto tiene que TUMBAR el sondeo para que el hook reinstale.
if [ -f "$MARCA" ] && python3 -c "import pytest, jsonschema, pandas, httpx, dotenv, anthropic, openai, voyageai, cryptography, openpyxl" 2>/dev/null; then
  anotar saltada
  echo "deps: ya instaladas (${REQ_HUELLA:0:8}) — se salta la instalación"
  exit 0
fi

$PIP --ignore-installed PyJWT cryptography
grep -v '^langdetect' requirements.txt > /tmp/req_sin_langdetect.txt
sed 's|^-r requirements.txt|-r /tmp/req_sin_langdetect.txt|' requirements-dev.txt \
  > /tmp/req_dev_filtrado.txt
$PIP -r /tmp/req_sin_langdetect.txt -r /tmp/req_dev_filtrado.txt
$PIP langdetect || echo "AVISO: langdetect no instalado (tolerado)"
$PIP pytest jsonschema pandas openpyxl \
  lingua-language-detector psycopg2-binary
rm -f "${MARCA_DIR}/.technical_bot_deps_"*   # sin huérfanos de huellas viejas (Fable r2)
touch "$MARCA"
anotar instalada
echo "deps: instaladas (${REQ_HUELLA:0:8})"
