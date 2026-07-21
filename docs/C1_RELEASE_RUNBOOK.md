# C1: contrato de release y runbook

Estado a 2026-07-21: **P1 `CODE_READY`, ejecución exacta autorizada y
`P1_MIGRATION_VERIFIED_CREDENTIALS_PENDING`; todavía no existe GO de release**. La
autorización humana cubre una única P1 de 27 réplicas/27 generaciones y exactamente
81 llamadas pagables, con techo duro de 10 USD; no cubre merge, deploy ni canary. Además de
los PASS previos de ensamblaje offline y reachability GET-only, están implementados
el adapter productivo, el cierre transitivo exacto, la captura read-only de Railway,
el manifest live pre/watch/post, el fence PostgreSQL persistente read-only por IPC,
el guard PostgREST acotado y el executor. El control histórico gratuito conserva el
prior PEARL 7-vs-8 en 3/3. La migración `p1_readonly` quedó aplicada y verificada
en producción como versión `20260721120000`; no existe `P1_PASS`, no se ejecutaron
llamadas pagadas, no se cambió Railway y no hubo deploy.

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
python -m scripts.s277_c1_release_gate
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
python -m scripts.s277_c1_live_reachability_probe `
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

## Gate pagado prerelease: implementación lista, ejecución pendiente

La respuesta real aportada por Alberto tenía 4.449 caracteres y Telegram la
dividió en dos mensajes: fue una generación, no dos respuestas. Tampoco
incluyó los dos avisos de F12. Por tanto, reachability no basta.

Antes de encender C1 hay que ejecutar un runner reproducible sobre los 13 QIDs
cuyo contexto structural cambia:

```text
cat001, cat017, cat018, cat019,
hp002, hp003, hp005, hp011, hp012, hp013, hp014, hp017, hp018
```

Contrato implementado por el runner end-to-end:

- cada réplica atraviesa retrieval, rerank, contexto servido combinado —con sólo
  structural entre las lanes de coverage y preservando exactamente las capacidades
  ortogonales vivas—, síntesis y renderer reales por el seam actual;
  no usa el contexto congelado S113;
- modelo y parámetros exactos congelados;
- dos réplicas por QID y una tercera de hp017: 27 generaciones y exactamente
  81 llamadas pagables a modelos contando embedding, rerank y síntesis;
- WAL antes de cada llamada física, cero reintentos automáticos y receipts de
  pool, prefijo, contexto, envelope, respuesta y render por réplica;
- reapertura de 81 responses + 81 watches y revalidación semántica completa de
  las 27 réplicas en resume, score y finalize; exactamente 162 eventos WAL
  reserve/completed, con orden, modelo, usage y presupuesto recomputados;
- ventana de corpus protegida por fence de operador separado y fingerprints
  pre/post; el runner usa sólo identidad PostgREST read-only;
- bound estático conservador de **6,777 USD**, techo duro de **10 USD** y parada
  temprana ante cualquier regresión dura;
- scorer determinista de los dos avisos y sus citas en hp017;
- adjudicación fact-level contra los facts ya OK para los otros 12 QIDs;
- artefacto con hashes de código, config, contextos y respuestas completas.

Artefactos canónicos: `evals/s277_c1_p1_prereg_v1.yaml`,
`evals/s277_c1_p1_fact_contract_v1.json`,
`evals/s277_c1_p1_release_config_schema_v1.json` y
`evals/s277_c1_p1_design_v1.md`. Para inspeccionar el plan y la interfaz sin
consumir red ni presupuesto:

```powershell
python -m scripts.s277_c1_p1 plan
python -m scripts.s277_c1_p1 score-stored-controls
python -m scripts.s277_c1_p1 run --help
```

Las stop-lines por adapter ausente, manifest live ausente y cierre transitivo
incompleto están retiradas. El adapter ejecuta el path productivo y liga receipts de
embedding, rerank y síntesis a la attestation de cada réplica; el conjunto exacto de
módulos ejecutados forma parte del closure sellado. El manifest observa y compara
pre/watch/post firmas y definiciones RPC, ACL/owners/overloads, índices, relaciones,
RLS, extensiones, roles y configuración PostgREST. El fence mantiene una sesión
PostgreSQL read-only y locks persistentes desde un operador separado; el runner sólo
recibe su IPC sin credenciales y puede solicitar cierre o aborto explícitos.

Eso deja credenciales e inputs operativos, no otro desarrollo: la migración versionada
`20260721120000_add_p1_readonly_role.sql` está aplicada y sus postcondiciones pasaron.
La `SUPABASE_KEY` PostgREST y la credencial PostgreSQL del operador están disponibles
fuera del candidato; el PAT de Supabase ya está provisionado de forma efímera y falta
el bearer efímero `P1_SUPABASE_JWT` con `role=p1_readonly`.
`SUPABASE_KEY` alimenta exclusivamente el encabezado `apikey` y no puede reutilizarse
como bearer; `P1_SUPABASE_JWT` alimenta `Authorization: Bearer ...` y no puede
reutilizarse como `apikey`. `run` sigue fallando cerrado sin `--execute`,
`--confirm-paid`, el recibo materializado de la autorización ya otorgada y todos los
inputs live. Ninguno de esos inputs puede quedar en Git.

La prueba `transaction_read_only=on` del endpoint de identidad corresponde sólo a
ese GET. Los POST `/rpc/...` no se consideran seguros por el verbo HTTP ni por ese
receipt: su seguridad efectiva procede de ACL/RLS del rol mínimo, la allowlist exacta
del guard y la comprobación de que no haya ninguna función `SECURITY DEFINER`
accesible. En el PostgreSQL 17 alojado la migración debe verificar además tres grants
exactos y no heredables: `authenticator <- postgres` con `SET TRUE/ADMIN FALSE`,
`postgres <- postgres` con `SET TRUE/ADMIN FALSE`, y el grant automático de creador
`postgres <- supabase_admin` con `SET FALSE/ADMIN TRUE`. Los dos últimos se combinan
para permitir `SET ROLE` sin herencia y conservar la administración inevitable del rol.
La migración aplica y verifica precisamente esa frontera; no debe emitirse
`P1_SUPABASE_JWT` antes de que todas sus postcondiciones pasen.

La ejecución futura tampoco acepta rutas de persistencia elegidas por el adapter:
WAL y sidecars viven bajo `artifact_root` con nombres canónicos y el ledger global se
deriva de su directorio padre. El genesis sella ese layout. Si un claim ya existe y
falta cualquiera de los estados durables originales, el runner devuelve
`HOLD_AUTHORIZATION_RESUME_STATE`; no reconstruye el run ni renueva presupuesto.
Un lease `O_EXCL` indexado por artifact root serializa el proceso antes de claim/bind;
un competidor devuelve `HOLD_RUN_LEASE_ACTIVE` sin tocar WAL/result. Runtime exacto,
ownership del lease y request reservado se vuelven a comprobar antes de cada send.
El genesis añade un snapshot canónico de modelos, inputs, presupuesto e hashes de
implementación. Toda reapertura reconstruye las 81 llamadas físicas, valida los 162
eventos WAL alternos y exige que coste observado/acumulado y `result.budget`
coincidan exactamente; un artefacto re-sellado pero semánticamente inválido queda
en HOLD/NO-GO.

Este lease local sólo autoriza ejecución **single-host**. OneDrive no lo convierte en
lock distribuido. Un lease abandonado no se borra por edad ni se autoreclama: hasta
que exista un protocolo separado de recuperación stale, su presencia es un HOLD
manual. Un runner multi-host necesitará exclusión transaccional externa revisada.

Una única réplica por pregunta no autoriza un criterio absoluto de cero
regresiones. Tampoco basta `query_logs`: `src/logging_db.py` trunca la columna
`response` a 4.096 caracteres y el recibo privacy-safe no persiste el texto de los átomos.
`test_bot_vs_gold.py` ya cruza el seam RAG servido y registra el estado de
coverage, pero aún no implementa las repeticiones, checkpoint de coste ni el
artefacto preregistrado de esta fase; no se puede usar como sustituto informal.
Su salida usa un nombre nuevo que incluye el release profile. Los consumidores
históricos de `bot_vs_gold_results_k5.yaml` no migran automáticamente: P1 debe
pasar el artefacto nuevo de forma explícita o consumirlo desde su runner sellado.

### Fase P1: ejecución autorizada, prerrequisitos pendientes

El runner anterior se ejecuta sobre el commit candidato **antes de cualquier
despliegue**. Primero lee Railway sin mutarlo y sella su snapshot; una transformación
pura preregistrada deriva `bootstrap_profile=off` y
`p1_target_profile=coverage_c1_v1`. P1 ejecuta el target derivado, no presupone que
Railway ya cambió. Su PASS sella tested commit/tree, manifest, planned patch, digest
de configuración común, fingerprints, contextos, respuestas y TTL de 6 horas. Si
árbol/código, configuración común, corpus, proveedor/runtime o TTL cambian después,
P1 caduca y debe repetirse bajo una preregistración nueva.

Secuencia operativa única para llegar a una decisión P1:

1. **Completado:** migración `20260721120000_add_p1_readonly_role.sql` aplicada y
   verificada, incluidas las tres filas PostgreSQL 17 exactas descritas arriba.
2. Usar el PAT de Supabase ya provisionado fuera del checkout y crear un
   `P1_SUPABASE_JWT` efímero con `role=p1_readonly`; usar la `SUPABASE_KEY` existente sólo para `apikey` y la
   credencial PostgreSQL existente sólo en el operador. API key y bearer son
   credenciales separadas y el runner no recibe la credencial PostgreSQL.
3. Capturar desde el checkout limpio y detached el release-config Railway read-only,
   el contrato/manifest live previo y la evidencia HTTP/identidad; emitir un recibo de
   autorización que materialice la decisión humana ya recibida, acepte expresamente
   el prior hp017 y limite la ejecución a 27 réplicas/81 llamadas y 10 USD.
4. Arrancar el operador de fence y ejecutar exactamente una vez `run --execute
   --confirm-paid` con `artifact-dir` e `ipc-dir` fuera del checkout y disjuntos.
5. `run` captura el manifest/snapshot posterior y cierra el fence —o lo aborta ante cualquier
   fallo— antes de retornar. Después, ejecutar `score` y `finalize`; sólo un resultado final
   sellado puede crear `P1_PASS`.

La autorización explícita ya recibida cubre sólo la P1 exacta de 27 réplicas/81 llamadas
bajo el techo de 10 USD. No constituye `P1_PASS` ni GO: siguen pendientes bearer,
inputs live, ejecución, `score` y `finalize`. Merge, deploy, migración de
trazas y canary pertenecen a la secuencia posterior y requieren autorización separada.

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
4. Durante ventana de mantenimiento y **antes del merge**, aplicar exactamente el
   `planned_bootstrap_patch` sellado por P1 como un único cambio Railway: eliminar
   `POST_RERANK_COVERAGE`, `STRUCTURAL_NEIGHBOR_COVERAGE`,
   `COVERAGE_MANDATORY_CALLOUT` y `MP_MANDATORY_VERB_TRIGGER`, junto con
   `COVERAGE_RELEASE_PROFILE=off`. Verificar el diff para no crear un
   estado intermedio inválido. El código viejo ignora el perfil nuevo y queda
   con coverage off; el código nuevo podrá arrancar de forma explícita.
5. Mantener `MUST_PRESERVE_CONTRACT=on`. El manifest debe fijar en `off`:
   `TABLE_PREAMBLE_CLOSURE`, `CANONICAL_HYQ_COVERAGE`,
   `COMPATIBILITY_BUNDLE_COVERAGE`, `RERANK_POOL_COVERAGE`,
   `STRUCTURAL_CASCADE_COVERAGE`, `LOGICAL_RECORD_COVERAGE`,
   `EVIDENCE_DERIVATION_OVERLAY`,
   `DEDUP_REFERENCE_NAVIGATION`, `R2_REPAIR_NAVIGATION`,
   `STRUCTURAL_NEIGHBOR_SHADOW`, `MP_HYBRID_DETECT`, `MP_SERVED_BINDING`,
   `MP_DEFLINE_EQ`, `MP_STEM_BINDING` y `MP_DISTINCTIVE_TOKEN`.
   `VISUAL_ASSETS_REGISTRY` no pertenece al perfil C1: debe conservar exactamente
   el valor vivo sellado (`on` en la foto documentada). Ausencia o drift deja el
   proceso en HOLD; P1 no lo apaga ni lo reactiva.
6. Mergear/desplegar el código y verificar arranque sano con profile `off`. El
   receipt de merge debe demostrar que el commit probado es ancestro/padre y que
   el tree SHA desplegado y el manifest son idénticos; squash/rebase o árbol distinto
   caducan P1 aunque el cambio parezca inocuo.
7. Repetir A y reemitir B desde un checkout del árbol exacto desplegado.
8. Con profile `off` y antes de `p1_expires_at`, verificar `bot_version`, lineage,
   tree, manifest, runtime, fingerprint y
   `common_config_sha256`. El único desacuerdo permitido con P1 es el profile:
   debe coincidir exactamente con `bootstrap_profile=off`. **No repetir las 27
   réplicas** si esa identidad es exacta; cualquier otro drift devuelve el
   proceso a P1.
9. Solo con P1 vigente y verificación post-deploy exacta, cambiar una variable
   durante ventana de mantenimiento:
   `COVERAGE_RELEASE_PROFILE=coverage_c1_v1`.
10. Tras el reinicio, verificar que la configuración completa coincide con
    `p1_target_profile`; cualquier delta aborta y revierte.
11. Ejecutar el canary post-activación: preguntar hp017 tres veces, puntuar las
    respuestas completas recibidas en Telegram y contrastar sus recibos en
    `query_logs.rag_trace`. Estas tres llamadas son verificación post-deploy, no
    una repetición del gate P1 de 27 réplicas; añaden normalmente 9 llamadas a
    modelos y requieren autorización/presupuesto separados.

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
- hp017 en P1 prerelease con target servido, callout exacto y ambos avisos
  correctamente citados en 3/3 réplicas;
- hp017 en el canary post-activación con el mismo contrato en 3/3 respuestas;
- cero pérdidas de los 43 facts del packet base transformado en las 27 ejecuciones
  preregistradas; `hp017#1` histórico es la exclusión explícita y versionada descrita
  en el contrato, no un fact silenciosamente omitido;
- cero conflictos o atribuciones inválidas detectadas respecto del packet,
  guardas, conflictos registrados y target; toda cita debe tener sintaxis/rango
  válido, sin afirmar que P1 inventarió toda prosa técnica adicional;
- cero truncamientos o errores de lane;
- trazas presentes, consistentes y dentro de la allowlist.

Un solo daño protegido, conflicto, error de identidad, `no_append` en hp017 o
ausencia de recibo implica NO-GO. El marcador canónico permanece en
**146/154 (94,81%)**: S277 no banca ningún hecho adicional; incluso un PASS P1
es un release gate sobre cohorte dev, no una adjudicación que mueva el KPI.

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

La migración P1 revocó el `EXECUTE` de `PUBLIC` sobre `create_hnsw_index()` y verificó
que `p1_readonly` no puede alcanzar ninguna función `SECURITY DEFINER`. El Advisor
posterior confirmó, sin embargo, grants explícitos preexistentes para `anon` y
`authenticated` sobre esa función. No bloquean la identidad mínima de P1, pero sí son
un riesgo separado que debe inventariarse y corregirse mediante una migración nueva
antes del GO final de C1. Revocarlos no formaba parte de la autorización actual y no se
ha ampliado silenciosamente el alcance. El rollout amplio de RLS también sigue fuera
de P1 y requiere tests y autorización propia.
