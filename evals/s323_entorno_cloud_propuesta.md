# s323 — Montar «dónde corre Claude»: cloud gobernable desde el móvil

Propuesta sometida al revisor adversarial (Protocolo 3, tier Fable standalone).
Impacto MEDIO: toca el arranque de TODA sesión cloud y la superficie de secretos.
No toca corpus, retrieval, idiomas ni esquema.

## Objetivo

Alberto quiere lanzar y gobernar trabajo desde el móvil. Estado previo: el
environment cloud estaba en **Default** (sin variables, red *Trusted*), lo que en
s315/s316 produjo dos fallos SILENCIOSOS: casmarglobal bloqueado por red, y
`OPENAI_API_KEY` ausente → el revisor Sol no era ejecutable y el dúo del
Protocolo 3 quedó cojo sin que nada avisara.

## Decisiones de Alberto (adjudicadas en la sesión, no propuestas mías)

1. Montar las **tres** superficies: cloud, Remote Control y Dispatch.
2. **Un solo environment con todas las keys** (rechazada mi recomendación de
   partirlo en dos por privilegio).
3. **Red Full** (rechazada mi recomendación de Custom con allowlist).

Riesgo aceptado y declarado en el doc y en la DEC: los environments no tienen
secret store; con red Full y la service key del corpus dentro, una sesión que lea
un portal o PDF hostil dispone de medio y destino para exfiltrar. Mitigación
operativa: environment personal (nunca compartido) + rotación ante sospecha.

## Cambios cableados

1. **`scripts/cloud_smoke.py` (nuevo)** — verificador del entorno de sesión (cloud
   o local) con recibo JSON en `evals/`. Comprueba: superficie y sesión, git no
   shallow, import REAL de módulos (no `find_spec`: el fallo de s315 era una
   `cryptography` deb que petaba con PanicException AL IMPORTAR), presencia de
   secretos (nunca su valor), y conectividad real a Supabase/Anthropic/OpenAI/
   Voyage + un portal de fabricante. Exit 1 si falla algo crítico.
2. **`tests/test_cloud_smoke.py` (nuevo)** — fija el contrato de no-fuga: con
   secretos falsos en el entorno, ningún valor aparece en stdout, stderr ni en el
   recibo; una key crítica ausente rompe el veredicto; el aviso de
   `TELEGRAM_BOT_TOKEN` solo se emite en sesiones cloud.
3. **`.claude/hooks/session-start.sh`** — idempotente: la instalación se salta si
   existe la marca `/tmp/.technical_bot_deps_<sha1(requirements+requirements-dev)>`
   Y un import real de `pytest, jsonschema, pandas, httpx, anthropic` funciona.
   Añadido `TB_PIP_CMD` para poder verificar el flujo en seco, y fallback
   `${CLAUDE_ENV_FILE:-/dev/null}` para que un `set -u` no aborte el hook DESPUÉS
   de haber instalado.
4. **`.claude/settings.json`** — `matcher: "startup|resume"` en el hook de arranque
   (antes corría en todos los eventos SessionStart, incluidos `compact`/`clear`),
   alineado con el ejemplo oficial y con el otro hook del repo.
5. **`docs/ENTORNO_CLOUD.md`** — reescrito contra la doc oficial vigente.

## Verificación hecha en el mismo turno

- `python scripts/cloud_smoke.py` en local: VEREDICTO LISTO, 0 críticos; los 5
  endpoints de red devolvieron HTTP 200.
- `tests/test_cloud_smoke.py`: 4/4.
- Hook: `bash -n` OK; dry-run pasada 1 instala + crea marca, pasada 2 la salta;
  sin `CLAUDE_CODE_REMOTE` es no-op.
- Corregidos dos falsos críticos propios tras comprobar el uso real: el SDK
  `supabase` está declarado en requirements pero NO lo importa nadie (la DB va por
  REST/httpx), y `jwt` no lo usa nadie (el hook instala PyJWT solo para apartar el
  paquete deb del sistema).

## Qué quiero que ataques

1. ¿Puede el centinela dejar una VM **sin dependencias** creyendo que las tiene?
   ¿Hay un camino donde la marca exista, los 5 imports pasen y aun así falte algo
   que la suite necesita?
2. ¿`matcher: "startup|resume"` deja algún evento real de sesión cloud sin hook?
3. ¿Hay algún camino por el que `cloud_smoke.py` filtre un secreto (mensajes de
   error de httpx con la URL, `r.text` de una respuesta, el recibo)?
4. ¿El criterio crítico/no-crítico de keys y módulos es correcto para el trabajo
   real de este repo?
5. ¿Afirma el doc algo que el código no sostiene?
