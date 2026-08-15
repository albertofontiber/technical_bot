# Entorno cloud y trabajo «on the go» — dónde corre Claude

> **Objetivo.** Lanzar y GOBERNAR el trabajo desde el móvil con la misma autonomía
> que en local. Reescrito en **s323** contra la documentación oficial vigente: la
> versión anterior (s315c) mandaba a un menú «Environments» que ya no se llama así
> y daba por buena una lista de secretos que hoy tiene una advertencia explícita.

## 1. Las tres superficies (el selector «dónde corre Claude»)

No es una superficie, son tres, y cubren mitades distintas del trabajo de ESTE repo:

| Superficie | Dónde corre | Qué cubre aquí | Qué NO |
|---|---|---|---|
| **Cloud session** | VM de Anthropic (Ubuntu 24.04) | evals, sondas, harness, código, docs, DB, harvest de portales. **Sigue con el PC apagado** | **OneDrive**: PDFs del corpus y el extraction store → ingesta y fase de enunciados |
| **Remote Control** | **Tu PC**, dirigido desde móvil/web | justo lo que cloud no cubre: OneDrive, `.env`, MCPs locales, todo el entorno real | necesita el PC encendido; sin paralelismo |
| **Dispatch** | App de escritorio | mensajear una tarea desde el móvil y que ella la ejecute | ídem PC encendido (Pro/Max) |

**Dónde está el selector:** el icono de nube en la fila de encima del cuadro de
mensaje, en claude.ai/code, en la app de escritorio y en la app móvil. No hay
página de ajustes ni URL directa. Ahí se crean y editan los environments, y ahí
está la sección de Remote Control.

**Regla de decisión:** ¿el trabajo toca PDFs/OneDrive? → Remote Control. ¿Es
evals, DB, código o docs y quieres cerrar el portátil? → Cloud. Doc oficial:
<https://code.claude.com/docs/en/claude-code-on-the-web> ·
<https://code.claude.com/docs/en/cloud-environments> ·
<https://code.claude.com/docs/en/remote-control>

## 2. Qué es automático (versionado en el repo, no en la web)

- **`.claude/hooks/session-start.sh`** — deja el contenedor listo: dependencias con
  sus tres workarounds (langdetect, PyJWT/cryptography de deb, requirements-dev
  arrastrando el base), **historial git COMPLETO** (los tests de contratos congelados
  leen blobs viejos; sin `unshallow` fallan ~180) y `PYTHONPATH=.`. Corre solo si
  `CLAUDE_CODE_REMOTE=true`, que es la variable canónica documentada.
  **s323: idempotente** — un `resume` ya no reinstala (centinela = huella sha1 de los
  requirements + import real; si cambian los requirements o la VM es nueva, reinstala).
- **`scripts/cloud_smoke.py`** — verificador del entorno con recibo. Es el
  instrumento del Protocolo 1 aquí: sin él, «el cloud funciona» es una declaración
  sin comprobar. Contrato fijado en `tests/test_cloud_smoke.py`: **nunca vuelca el
  valor de un secreto** — solo presencia y longitud. Todo detalle pasa por un
  saneador único antes de imprimirse o serializarse, porque las dos vías de fuga
  reales no son la lista de keys sino los mensajes de error de httpx (llevan la
  URL dentro) y `r.text` de una respuesta 4xx; y la URL del remote se publica sin
  su `usuario:token@` (en un clon cloud viene con credencial embebida). Los cuatro
  caminos están cubiertos por test, red incluida, con transporte simulado.

```
python scripts/cloud_smoke.py                # entorno + deps + keys + conectividad
python scripts/cloud_smoke.py --sin-red      # sin llamadas a APIs
python scripts/cloud_smoke.py --sin-dotenv   # desde LOCAL, simula lo que vería el cloud
```

**Qué llega y qué no a una sesión cloud** (sale de un clon fresco del repo):

| Llega | No llega |
|---|---|
| `CLAUDE.md`, `docs/`, `.claude/settings.json` y sus hooks | `~/.claude/CLAUDE.md`, skills, agentes y comandos de usuario |
| Lo que esté commiteado, sin más | MCPs locales — este repo **no tiene `.mcp.json`**: en cloud la DB se toca por REST con `SUPABASE_*`, no por MCP |
| Los tests, los golds, los recibos | El `.env` (por eso las keys van al environment) y **OneDrive** |

## 3. Checklist de Alberto (una vez, ~10 min)

### 3.1 Environment cloud

Selector de nube → **Add cloud environment** (o el engranaje del existente).

- **Network access: Full.** Decisión de Alberto en s323 (DEC-220). *Trusted* —el
  nivel por defecto— es lo que bloqueó casmarglobal en s315 y deja fuera Supabase,
  Voyage y OpenAI.
- **Environment variables** (formato `.env`, un `KEY=value` por línea; los valores
  están en tu `.env` local / dashboard de Railway):

| Variable | Para qué | ¿Imprescindible? |
|---|---|---|
| `SUPABASE_URL` | scripts contra la DB (harness, sondas, loaders) | sí |
| `SUPABASE_SERVICE_KEY` | ídem — los SCRIPTS leen esto, el MCP no llega | sí |
| `ANTHROPIC_API_KEY` | generadores, harness, sondas, revisor Fable | sí |
| `VOYAGE_API_KEY` | embeddings de `chunks_v2` (retrieval real) | sí |
| `OPENAI_API_KEY` | **revisor Sol del dúo (Protocolo 3)** y juez | sí — sin ella, s316 se repite |
| `RAILWAY_TOKEN` | censo de flags y variables vivas de producción | opcional |
| `NOTIFIER_USER` / `NOTIFIER_PASSWORD` | harvest del portal Notifier | opcional |
| `LLAMA_CLOUD_API_KEY` | LlamaParse, solo si se ingesta desde cloud | opcional |

**NO añadir `TELEGRAM_BOT_TOKEN`**: el bot vive en Railway y un script haciendo
polling en una sesión cloud competiría con producción, robándole updates a los
técnicos. `cloud_smoke.py` avisa si aparece.

**Riesgo aceptado (DEC-220):** los environments **no tienen secret store** — la
doc oficial desaconseja meter credenciales, porque son legibles por cualquiera que
use el environment. Con red *Full* y la service key del corpus dentro, una sesión
que lea un portal o un PDF hostil tiene, en principio, con qué exfiltrar. Se acepta
a cambio de que ninguna sesión se quede a medias por una política de red, y la
mitigación es operativa: environment **personal** (nunca compartido) y **rotar
keys** ante cualquier sospecha. Partirlo en dos environments por privilegio
(`código` sin service key / `datos` con ella) son 2 minutos en el mismo selector el
día que se prefiera.

### 3.2 Smoke de recepción (sin esto no está montado)

En la primera sesión cloud del environment nuevo:

```
python scripts/cloud_smoke.py && python -m pytest -q && python scripts/check_deps.py
```

Debe dar `VEREDICTO: LISTO` y la suite en verde. El recibo queda en
`evals/s323_cloud_smoke_v1.json` y se commitea: es la prueba fechada de que ese
environment sirve. Repetir cuando caduque el caché (~7 días) o al tocar una variable.

### 3.3 Móvil, Remote Control y Dispatch

- **App**: Claude para iOS/Android, misma cuenta claude.ai → pestaña **Code**. Ahí
  aparecen las sesiones cloud y las de Remote Control.
- **Remote Control** (para lo que necesita OneDrive): en la sesión local, `/remote-control`;
  o `claude remote-control` al arrancar. Luego, en el móvil, pestaña **Code** → elegir
  la sesión (o escanear el QR que muestra el terminal). Da notificaciones push cuando
  termina algo largo o cuando Claude necesita una decisión.
- **Dispatch**: mensajear la tarea a la app de escritorio desde el móvil.
- **Traer una sesión cloud al terminal**: `claude --teleport` (requiere árbol limpio,
  el mismo repo y la misma cuenta). Ojo: hoy no hay CLI `claude` en el PATH de esta
  máquina; desde la app de escritorio se usa el menú **Continue in**.

## 4. Trampas conocidas (medidas, no supuestas)

- **El dúo del Protocolo 3 es la primera víctima**: sin `OPENAI_API_KEY` en el
  environment, Sol no es ejecutable y una sesión cloud NO puede cerrar nada de
  impacto ALTO. Pasó en s315/s316 y el `cloud_smoke` lo marca como crítico.
- **`gh` no viene preinstalado** y `GH_TOKEN` vale `proxy-injected`: las herramientas
  de GitHub integradas funcionan, pero un script que lea `GITHUB_TOKEN` recibe el
  placeholder, no un token. El `git push` solo funciona contra la rama de la sesión.
- **Caché del environment**: el setup script se cachea ~7 días; el hook, no — corre
  en cada arranque (por eso ahora es idempotente). Si el arranque en frío duele, se
  puede mover la instalación a un setup script; medir primero con
  `echo $CLAUDE_PROJECT_DIR` para conocer la ruta real del clon.
- **Recursos del VM**: 30 GB de disco y memoria acotada — un `full` de un assessment
  grande puede no caber; esa clase de trabajo va por Remote Control.
- **Lo que no está pusheado no existe para una sesión cloud**: el VM clona el
  **remoto en tu rama actual**, no tu checkout. Hoy mismo el árbol local tiene
  scripts y recibos de s320/s322 sin commitear que una sesión cloud no vería.
- **Rate limits compartidos** con el resto de tu uso de Claude: varias sesiones
  cloud en paralelo consumen proporcionalmente.
- **Reconciliar al volver a local** (lección s316): tras una tanda de sesiones cloud,
  lo primero es `git fetch` + revisar qué se mergeó. El estado canónico sigue siendo
  el bloque «Estado actual» de `docs/PLAN_RAG_2026.md`.

## 5. Backup lógico del corpus (s319, DEC-209 — correr en LOCAL, no en cloud)

Tras cada lote de ingesta (mínimo: mensual):

```
python scripts/backup_supabase.py --data-root "C:\Users\Admin\OneDrive - fontiber com\Documents\Claude\Technical Bot"
```

Vuelca la capa corpus/identidad (documents + chunks_v2 + enunciados + hyq, sin
embeddings ni PII) a `<data-root>/backups/<UTC>/` y NO da recibo sin pasar el
drill de restauración (SQLite + counts + FK). Recibo en `evals/`. RPO ≤1 lote;
RTO horas. La capa de datos personales queda FUERA a conciencia (retención RGPD
— DEC-209 [DECIDIR]); el desastre total lo cubre el backup gestionado de
Supabase. Retención de dumps: 3 rotaciones (borrar la más vieja al crear la 4ª).
