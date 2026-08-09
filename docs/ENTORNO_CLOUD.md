# Entorno cloud (Claude Code en la web) — lanzar trabajo «on the go»

> **Objetivo.** Poder lanzar sesiones desde el móvil/web (claude.ai/code) con la
> misma autonomía que en local. **Qué es automático desde s315c**: el hook de
> arranque (`.claude/hooks/session-start.sh`, versionado) deja el contenedor listo
> — dependencias con sus tres workarounds (langdetect, PyJWT/cryptography de deb,
> requirements-dev arrastrando el base), historial git COMPLETO (los tests de
> contratos congelados leen blobs viejos; sin unshallow fallan ~180) y
> `PYTHONPATH=.`. Validado en s315c: suite, `check_deps`, `catalog_store validate`
> y `gold_store validate` en verde en el contenedor web.

## Checklist de Alberto (una vez, ~10 min, en claude.ai/code → Environments)

Documentación oficial: https://code.claude.com/docs/en/claude-code-on-the-web

### 1. Variables de entorno (secretos)

Añadir al environment del repo (los valores están en tu `.env` local / dashboard
de Railway):

| Variable | Para qué |
|---|---|
| `SUPABASE_URL` | scripts contra la DB (harness, sondas, loaders) |
| `SUPABASE_SERVICE_KEY` | ídem (la sesión ya llega a la DB por MCP, pero los SCRIPTS leen esto) |
| `ANTHROPIC_API_KEY` | generadores (enunciados/hyq), harness, sondas |
| `VOYAGE_API_KEY` | embeddings (retrieval real, cargas de canales) |
| `OPENAI_API_KEY` | el revisor Sol del dúo (`adversarial_review.py`) — sin ella el dúo queda cojo en cloud |
| `LLAMA_CLOUD_API_KEY` | solo si se va a ingestar desde cloud (LlamaParse) |

**NO añadir `TELEGRAM_BOT_TOKEN`**: el bot vive en Railway; un script suelto en
una sesión cloud haciendo polling competiría con producción.

### 2. Política de red

La política restrictiva de hoy bloqueó casmarglobal.com (recon s315). Para las
sesiones de harvest/eval, permitir al menos:

- `api.anthropic.com` · `api.voyageai.com` · `api.openai.com`
- `*.supabase.co`
- portales de corpus: `casmarglobal.com` · `firesecurityproducts.com` ·
  `notifier.es` · `morley-ias.es` (y los que traigan las marcas nuevas)

(o política abierta si prefieres no mantener la lista).

### 3. Lo que el cloud NUNCA tendrá

**OneDrive** (los PDFs del corpus y el extraction store
`data/extraction/agent_anthropic-sonnet-45/`). Consecuencia: la fase de
enunciados de `derive_channels_lote.py` y las re-ingestas necesitan máquina
local, salvo que algún día subamos el store a un bucket (opción anotada, no
decidida). El resto — evals, sondas, harvest de portales, hyq (lee de la DB),
código, DB, docs — corre en cloud con los pasos 1-2 hechos.

## Cómo lanzar trabajo on the go

claude.ai/code (web o móvil) → New session sobre `albertofontiber/technical_bot`
→ escribir el encargo. El arranque canónico de cualquier sesión es el bloque
«Estado actual» de `docs/PLAN_RAG_2026.md` (CLAUDE.md lo manda leer), así que un
encargo de una línea («sigue con X del PLAN») basta.
