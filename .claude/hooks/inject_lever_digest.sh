#!/bin/bash
# Inyecta docs/LEVER_DIGEST.md en el contexto de CADA sesión (DEC-072).
#
# POR QUÉ existe: el fallo que DEC-072 diagnosticó no era canon ausente, era canon
# NO CONSULTADO (negar que el filtro de `category` existía; olvidar que
# contextual-retrieval ya se había probado). Un doc que «debo acordarme de abrir»
# hereda la dependencia que falló ⇒ hook, no nota.
#
# POR QUÉ está VERSIONADO (s316, corrige el gap declarado de DEC-072): DEC-072 lo
# dejó gitignored y declaró el riesgo — «setup local por checkout». Se materializó:
# el hook desapareció de la máquina local y las sesiones cloud (s315) nunca lo
# tuvieron. Desde s315c `.claude/` versiona el arranque, así que este hook viaja con
# el repo y el control deja de depender del checkout.
#
# Fail-open a propósito: si el digest no está, la sesión arranca igual (rc=0).
set -euo pipefail

RAIZ="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
DIGEST="$RAIZ/docs/LEVER_DIGEST.md"

[ -f "$DIGEST" ] || exit 0

echo "=== docs/LEVER_DIGEST.md (inyectado por hook · DEC-072) ==="
echo "Veredicto VIGENTE de cada lever medido. Antes de proponer, opinar o NEGAR sobre"
echo "un lever o un hecho estructural: cita la MÉTRICA del veredicto y verifica que"
echo "coincide con el objetivo de HOY (settled-en-PASS != settled-en-retrieval-miss)."
echo
cat "$DIGEST"
