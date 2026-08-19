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

# El sondeo incluye `cryptography` A PROPÓSITO: su PanicException de s315 salta AL
# IMPORTAR, y un sondeo que no lo tocase daría por buena una VM rota. La lista es
# TODOS los módulos críticos de scripts/cloud_smoke.py (contrato s323, completado
# en s325g: faltaban dotenv y openpyxl) — importa más ahora que un falso salto no
# muere con la VM sino que viaja en el snapshot ~7 días (hallazgo Fable s325g):
# cualquier crítico roto tiene que TUMBAR el sondeo para que el hook reinstale.
if [ -f "$MARCA" ] && python3 -c "import pytest, jsonschema, pandas, httpx, dotenv, anthropic, openai, voyageai, cryptography, openpyxl" 2>/dev/null; then
  echo "deps: ya instaladas (${REQ_HUELLA:0:8}) — se salta la instalación"
  exit 0
fi

# Traza de diagnóstico (s325h-c). Llegados aquí SE VA A REINSTALAR, y hay tres causas
# con arreglos OPUESTOS: (a) la VM no traía nada — el snapshot no persiste purelib;
# (b) traía un marcador de huella CADUCA — persiste, pero algo entró en la huella
# (este script entra en la suya, así que editarlo invalida a propósito); (c) traía la
# huella VIGENTE y lo que falló fue el sondeo de imports — persiste y hay corrupción.
# El `rm -f` de huérfanos de más abajo borra justo esa evidencia antes de estampar, así
# que se imprime ANTES de instalar (también si pip revienta después). Medido en s325h-c:
# 163/164 entradas de purelib escritas después del boot de la VM ⇒ caso (a), no viaja nada.
# Va en subshell con `|| true` A PROPÓSITO (hallazgo Fable r1): bajo `set -e`, un `date`
# sin `-r`, un MARCA_DIR ilegible o cualquier sorpresa del entorno matarían el arranque en
# una ruta que ANTES no podía fallar. Esto es diagnóstico: si no puede hablar, calla.
(
  for _m in "${MARCA_DIR}"/.technical_bot_deps_*; do
    [ -e "$_m" ] || { echo "deps: la VM no traía NINGÚN marcador en ${MARCA_DIR} — el snapshot no persiste purelib O el build de la caché no corrió/falló (no distingue: eso es del dashboard)"; break; }
    _h="${_m##*_}"
    if [ "$_m" = "$MARCA" ]; then _q="huella VIGENTE → falló el sondeo de imports"; else _q="huella caduca → el snapshot SÍ persistió"; fi
    echo "deps: marcador previo ${_h:0:8} mtime=$(date -u -r "$_m" +%Y-%m-%dT%H:%M:%SZ) — ${_q}"
  done
) || true

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
echo "deps: instaladas (${REQ_HUELLA:0:8})"
