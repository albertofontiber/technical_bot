# C1: contrato de release y runbook

Estado a 2026-07-20: **PASS de ensamblaje offline y PASS GET-only desde el
prefijo congelado; NO-GO de release hasta el gate pagado de síntesis**. No se ha
cambiado Railway ni aplicado la migración. Los instrumentos S277 no han
realizado llamadas pagadas.

## Qué corrige

El probe S274 demostró que el tratamiento C1 funciona cuando el chunk de
cobertura ya está servido. No atravesaba el fetch/selector live. En Railway
estaban activos `COVERAGE_MANDATORY_CALLOUT` y `MP_MANDATORY_VERB_TRIGGER`, pero
no el master ni la lane structural; por eso ambos eran inalcanzables.

`COVERAGE_RELEASE_PROFILE=coverage_c1_v1` convierte estas cuatro piezas en una
unidad atómica:

- `POST_RERANK_COVERAGE=on` efectivo.
- `STRUCTURAL_NEIGHBOR_COVERAGE=on` efectivo.
- `COVERAGE_MANDATORY_CALLOUT=on` efectivo.
- `MP_MANDATORY_VERB_TRIGGER=on` efectivo.

El perfil exige `MUST_PRESERVE_CONTRACT=on` y el resto de lanes de coverage en
`off`. Los parámetros de llamada no pueden sobreescribir un perfil explícito.
El seam valida que coverage solo añada hasta cuatro chunks con identidad: si
quita, muta, reordena o desborda el prefijo del reranker, degrada al prefijo
original y registra `status=error`.

`legacy` queda solo para harnesses offline. Cualquier worker de producción
(Telegram, web o futuro multi-turn) debe arrancar con un perfil explícito
`off` o `coverage_c1_v1`; esta regla es independiente del transporte.

## Qué prueban exactamente los dos instrumentos

### A. Ensamblaje offline, sin red

```powershell
python scripts/s277_c1_release_gate.py
```

Resultado requerido: `PASS_C1_ASSEMBLY_OFFLINE`. El instrumento:

- usa el seam que utiliza Telegram;
- conserva el prefijo hp017 de 10 filas;
- ejecuta el selector sobre los dos candidatos que S108 ya había seleccionado;
- revalida y sirve el callout exacto del target como F12;
- fuerza una cita `[F12]` para probar el contrato must-preserve;
- ejecuta además un control negativo sin citas, en el que los avisos no se
  añaden;
- bloquea conexiones socket y usa transporte Anthropic falso.

El runner sobreescribe de forma explícita todos los flags que pueden alterar
este recorrido (coverage, planner, generator, identidad, visuales y variantes
`MP_*`) y publica el snapshot no secreto efectivo en su salida. Un `.env` hostil
no puede convertir una variante experimental en parte accidental del PASS.

Por diseño, **no prueba reachability live ni que el modelo decida citar F12**.
El control negativo hace imposible confundir este PASS con una corrección
determinista del synthesis miss.

### B. Neighbor-fetch live desde prefijo congelado, GET-only y sin modelo

```powershell
python scripts/s277_c1_live_reachability_probe.py `
  --confirm-live-read-only `
  --env-file <ruta-segura-al-env>
```

Resultado observado y requerido sobre el runtime sellado:

```json
{
  "probe": "PASS_C1_LIVE_NEIGHBOR_FETCH_FROM_FROZEN_PREFIX_READ_ONLY",
  "seed_rows": 10,
  "fetched_candidate_rows": 110,
  "rows_read": 120,
  "http_get_requests": 5,
  "served_rows": 12,
  "target_fragment": 12,
  "target_callout_receipted": true,
  "database_writes": 0,
  "paid_model_calls": 0,
  "uses_frozen_retrieval_prefix": true,
  "proves_live_retrieval": false,
  "proves_live_rerank": false,
  "proves_model_synthesis": false
}
```

El cliente del probe expone exclusivamente `GET`. El fetcher PostgREST, el
selector, la attestation, el límite de append y el seam son reales. Retrieval y
rerank se sustituyen por el prefijo S113 sellado: el PASS demuestra que, **dado
ese prefijo**, el fetch live devuelve 110 filas raw pre-selector y el target
llega a F12. Esas 110 filas pueden incluir las diez seeds y no equivalen a 110
competidores elegibles. Retrieval/rerank actuales y la respuesta quedan para el
gate pagado.

El probe emite un manifest transitivo con hashes LF-normalizados de los módulos
y YAML que participan en este path structural-only. El test exige el conjunto
exacto; cualquier cambio en fetch, selector, attestation, perfil o config
invalida el recibo. El JSON versionado actual es autoridad sólo para este
checkout byte-idéntico; no debe repinnearse editando hashes: ante cualquier
drift hay que reejecutar el GET-only y guardar su nueva salida.

## Gate pagado prerelease pendiente

La respuesta real aportada por Alberto tenía 4.449 caracteres y Telegram la
dividió en dos mensajes: fue una generación, no dos respuestas. Tampoco
incluyó los dos avisos de F12. Por tanto, reachability no basta.

Antes de encender C1 hay que congelar y ejecutar un runner reproducible sobre
los 13 QIDs cuyo contexto structural cambia:

```text
cat001, cat017, cat018, cat019,
hp002, hp003, hp005, hp011, hp012, hp013, hp014, hp017, hp018
```

Contrato mínimo del runner todavía pendiente en este cambio:

- contexto structural-only producido por el seam actual, no el contexto
  combinado S113;
- modelo y parámetros exactos congelados;
- dos réplicas por QID y una tercera de hp017 (27 llamadas máximo);
- checkpoint antes de cada nueva llamada y cero reintentos automáticos;
- techo duro de **10 USD** y parada temprana ante cualquier regresión dura;
- scorer determinista de los dos avisos y sus citas en hp017;
- adjudicación fact-level contra los facts ya OK para los otros 12 QIDs;
- artefacto con hashes de código, config, contextos y respuestas completas.

Una única réplica por pregunta no autoriza un criterio absoluto de cero
regresiones. Tampoco basta `query_logs`: la columna `response` se trunca a
4.096 caracteres y el recibo privacy-safe no persiste el texto de los átomos.
`test_bot_vs_gold.py` ya cruza el seam RAG servido y registra el estado de
coverage, pero aún no implementa las repeticiones, checkpoint de coste ni el
artefacto preregistrado de esta fase; no se puede usar como sustituto informal.
Su salida usa un nombre nuevo que incluye el release profile. Los consumidores
históricos de `bot_vs_gold_results_k5.yaml` no migran automáticamente: P1 debe
pasar el artefacto nuevo de forma explícita o consumirlo desde su runner sellado.

### Fase P1: autorización pagada prerelease

El runner anterior se ejecuta sobre el commit candidato **antes de cualquier
despliegue**. Su artefacto PASS debe sellar commit, manifest de implementación,
flags, contextos y respuestas. Si código, config o contextos cambian después,
el PASS caduca y P1 debe repetirse bajo una preregistración nueva.

## Trazabilidad y privacidad

La migración añade `query_logs.rag_trace JSONB` nullable en la misma fila
consentida. No crea tabla, FK ni índice. Revalida `RLS`, `FORCE RLS`,
`service_role.BYPASSRLS` y los grants. El constraint se recrea dentro de una
transacción explícita, por lo que un constraint homónimo con drift no puede dar
un falso positivo.

El payload `rag_serving_trace_v1` contiene únicamente:

- perfil y lane configurada;
- lanes realmente ejecutadas y estados allowlisted;
- contadores y recibo de integridad del prefijo;
- número de callouts exactos, revalidados y realmente appended;
- contadores must-preserve;
- número de partes y estado del renderer.

No persiste query adicional, contenido, citas, nombres de manual, QID, gold,
IDs de chunks/documentos/modelos ni números de fragmento. El sink vuelve a
validar la forma cerrada y descarta cualquier JSON arbitrario, aunque un caller
futuro se salte el builder.

Si el código llega antes que la columna y PostgREST devuelve de forma
definitiva `PGRST204`, `42703` o el check `23514`, el logger reintenta una vez
sin traza y emite un warning rate-limited. Nunca reintenta timeout o fallo de
red incierto, porque el primer insert podría haberse confirmado.

## Secuencia de despliegue, solo tras PASS de P1

1. Revisar el PR, pero **no mergearlo todavía**: Railway autodesplegaría un
   binario que exige perfil explícito sobre las variables legacy actuales.
2. Con Supabase CLI `2.109.1`, comprobar historial y dry-run:

   ```powershell
   npx --yes supabase@2.109.1 migration list
   npx --yes supabase@2.109.1 db push --linked --dry-run
   ```

3. Aplicar `20260720095702_add_query_logs_rag_trace.sql` mediante `db push` y
   ejecutar sus postcondiciones. No hacer cambios adicionales de RLS en este
   release.
4. Durante ventana de mantenimiento y **antes del merge**, aplicar como un único
   cambio de configuración Railway la eliminación de las cuatro variables
   legacy y `COVERAGE_RELEASE_PROFILE=off`. Verificar el diff para no crear un
   estado intermedio inválido. El código viejo ignora el perfil nuevo y queda
   con coverage off; el código nuevo podrá arrancar de forma explícita.
5. Mantener `MUST_PRESERVE_CONTRACT=on` y todas las lanes no C1 en `off`.
6. Mergear/desplegar el código y verificar arranque sano con profile `off`.
7. Repetir A y reemitir B desde un checkout byte-idéntico al commit desplegado.
8. Verificar que `bot_version`, manifest, flags y hashes de contexto coinciden
   exactamente con el artefacto P1. **No repetir las 27 llamadas** si la
   identidad es exacta; cualquier drift devuelve el proceso a P1.
9. Solo con P1 vigente y verificación post-deploy exacta, cambiar una variable
   durante ventana de mantenimiento:
   `COVERAGE_RELEASE_PROFILE=coverage_c1_v1`.
10. Ejecutar el canary post-activación: preguntar hp017 tres veces, puntuar las
    respuestas completas recibidas en Telegram y contrastar sus recibos en
    `query_logs.rag_trace`. Estas tres llamadas son verificación post-deploy, no
    una repetición del gate P1 de 27 llamadas.

Consulta operativa sin recuperar query ni respuesta:

```sql
select
  created_at,
  bot_version,
  chunks_used,
  rag_trace->>'release_profile' as release_profile,
  rag_trace#>>'{coverage,status}' as coverage_status,
  rag_trace#>'{coverage,configured_lanes}' as configured_lanes,
  rag_trace#>'{coverage,executed_lanes}' as executed_lanes,
  rag_trace#>>'{coverage,mandatory_callout_cards}' as receipted_callout_cards,
  rag_trace#>>'{must_preserve,status}' as mp_status,
  rag_trace#>>'{must_preserve,atoms_appended}' as atoms_appended,
  rag_trace#>>'{transport,message_parts}' as message_parts,
  rag_trace#>>'{transport,render_status}' as render_status
from public.query_logs
where rag_trace->>'release_profile' = 'coverage_c1_v1'
order by created_at desc
limit 10;
```

La traza prueba el recorrido genérico; el scorer de la respuesta completa es
quien prueba que se conservaron exactamente los dos avisos de hp017.

## Criterio GO / NO-GO

GO exige simultáneamente:

- A en PASS y un recibo B vigente sobre el commit candidato;
- gate pagado prerelease P1 en PASS, con identidad post-deploy exacta;
- hp017 con target servido, callout exacto y ambos avisos correctamente citados
  en 3/3 respuestas;
- cero pérdidas de facts previamente OK en las 27 ejecuciones preregistradas;
- cero conflictos, atribuciones incorrectas, citas inválidas, truncamientos o
  errores de lane;
- trazas presentes, consistentes y dentro de la allowlist.

Un solo daño protegido, conflicto, error de identidad, `no_append` en hp017 o
ausencia de recibo implica NO-GO. El marcador canónico permanece en
**146/154 (94,81%)**: S277 no banca ningún hecho adicional y su prueba de
reachability no sustituye una nueva adjudicación de síntesis.

## Rollback

Cambiar únicamente:

```text
COVERAGE_RELEASE_PROFILE=off
```

No desactivar `MUST_PRESERVE_CONTRACT`. Confirmar un arranque sano, ausencia de
lanes ejecutadas y una respuesta de control. La columna `rag_trace` se conserva:
es nullable y borrarla no mejora el rollback.

## Preparación para multi-turn y multi-hop

`src/rag/serving_pipeline.py` es el primitivo seguro de **un turno**, no el
orquestador multi-hop definitivo. El siguiente diseño deberá envolverlo con:

- estado request-scoped y almacenamiento de sesión separado del corpus;
- `conversation_id`, `turn_id`, `hop_id` e idempotency key;
- presupuesto de tokens, coste, hops y deadline por turno;
- planner que recupere/acumule evidencia sin sintetizar en cada hop;
- deduplicación y provenance del evidence set entre hops;
- una única síntesis final por defecto, con cancelación y trazas por hop;
- políticas explícitas de retención/RGPD y aislamiento entre usuarios.

Así C1 mejora el camino actual sin congelar prematuramente una arquitectura
multi-hop incompleta.

## Riesgo de seguridad separado

Supabase Advisor marca siete tablas públicas del corpus sin RLS y una función
`SECURITY DEFINER` ejecutable por `anon`/`authenticated`. No se corrige aquí:
activar RLS a ciegas podría romper retrieval. Requiere inventario de callers,
tests y rollout de permisos independiente.
