# s278 — Gate de seguridad TECH_DEBT #29: runbook RLS hardening

**ESTADO: NO-APLICADA — PENDIENTE DE VISTO DE ALBERTO.** La migración
`supabase/migrations/20260722120000_s278_rls_hardening.sql` está preparada y validada en
sintaxis, pero NO se ha ejecutado contra la DB live. Este gate es **stop-line** del cierre C1
(diseño `evals/s278_vnext_design_v2.md` §0.3, SEC-29 del dúo r1): bloquea el merge #184 aunque
todo lo demás pase. Aplicarla es una mutación live → requiere autorización explícita.

## Contexto (qué cierra y qué no)

- **Cierra:** la exposición confirmada por el Advisor (S277): RLS deshabilitado en
  `public.chunks_v2_enunciados` (22.842 filas observadas) + grants `SELECT/INSERT` de
  `anon`/`authenticated`, y los grants explícitos de `anon`/`authenticated` sobre
  `create_hnsw_index()` que `20260721120000` dejó pendientes (solo revocó `PUBLIC`, DEC-140).
  Además habilita RLS (default-deny, sin policies) en todas las tablas `public` del esquema
  versionado que no lo tenían declarado.
- **No toca:** `query_logs`/`feedback`/`user_consent` (RLS+FORCE desde `20260713164800`;
  `user_consent` nació con RLS), `identity_resolve_shadow` y `document_revision_lineages`
  (RLS desde su creación). No crea policies. No toca grants de `service_role` ni `p1_readonly`.
- **Invarianza esperada del bot:** el backend usa `SUPABASE_SERVICE_KEY` (`service_role`,
  `BYPASSRLS`) → conducta idéntica con o sin RLS. El smoke del paso 3 verifica esa invarianza.

### Inventario ESPERADO (del esquema versionado — el live es el paso 1)

| Relación `public` | Estado RLS esperado ANTES | Acción de la migración |
|---|---|---|
| `chunks` | sin RLS declarado (supabase_schema.sql) | ENABLE RLS |
| `chunks_v2` | RLS ya ON live (comentario `20260721120000` + policy p1) | ENABLE (no-op) |
| `chunks_v2_enunciados` | **sin RLS + grants anon/auth (CONFIRMADO Advisor)** | ENABLE RLS + REVOKE anon/authenticated/PUBLIC |
| `chunks_v2_hyq` | sin RLS declarado (migrations/013) | ENABLE RLS |
| `documents` | sin RLS declarado (migrations/001) | ENABLE RLS |
| `document_groups` | sin RLS declarado (migrations/001) | ENABLE RLS |
| `document_group_members` | sin RLS declarado (migrations/001) | ENABLE RLS |
| `document_visual_assets` | sin RLS declarado (migrations/014) | ENABLE RLS |
| `query_logs`, `feedback`, `user_consent` | RLS+FORCE (`20260713164800`) | ninguna |
| `identity_resolve_shadow` | RLS ON (`20260702165425`) | ninguna |
| `document_revision_lineages` | RLS ON (`20260722013000`) | ninguna |
| `create_hnsw_index()` (función) | EXECUTE anon/auth pendiente (DEC-140) | REVOKE anon/authenticated/PUBLIC |

### Residuales declarados

1. **`p1_readonly` (NOBYPASSRLS):** tras aplicar, sus `SELECT` sobre `chunks_v2_enunciados`,
   `chunks_v2_hyq`, `documents` y `document_visual_assets` devuelven 0 filas en silencio (solo
   `chunks_v2` y `document_revision_lineages` tienen policy p1). P1 está en SAFE HOLD con 0
   ejecución pagada → nada se rompe hoy; **antes de la próxima P1** hacen falta policies
   `FOR SELECT TO p1_readonly USING (true)` por tabla, con autorización separada (mismo patrón
   que `chunks_v2_p1_readonly_select`). Este gate NO las crea (scope = #29).
2. **Grants residuales en otras tablas:** los defaults de Supabase suelen otorgar privilegios a
   `anon`/`authenticated` en toda tabla `public`. La migración solo revoca los CONFIRMADOS
   (#29); el resto queda neutralizado por el default-deny de RLS (fila-cero) y se decide con el
   inventario del paso 1 (revocación extra = migración nueva, forward-only).
3. **Sin FORCE RLS:** deliberado — el owner (`postgres`) conserva sus rutas de mantenimiento.
4. **Este worktree no puede consultar la DB live** (regla de la lane): el inventario live es el
   paso 1, no un hecho ya verificado. La tabla de arriba es el esperado VERSIONADO + los dos
   hechos live confirmados por el Advisor/TECH_DEBT.

## Runbook (5 pasos, en orden; abortar en el primer desvío)

### Paso 1 — Inventario live (read-only, $0)

Con la query canónica de #29 más grants y policies:

```sql
-- RLS por tabla (query de TECH_DEBT #29)
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace
ORDER BY relname;

-- Grants de anon/authenticated sobre tablas public
SELECT table_name, grantee, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee IN ('anon', 'authenticated')
ORDER BY table_name, grantee, privilege_type;

-- Grants EXECUTE sobre funciones public
SELECT routine_name, grantee, privilege_type
FROM information_schema.routine_privileges
WHERE routine_schema = 'public' AND grantee IN ('PUBLIC', 'anon', 'authenticated')
ORDER BY routine_name, grantee;

-- Policies existentes
SELECT tablename, policyname, roles, cmd FROM pg_policies
WHERE schemaname = 'public' ORDER BY tablename, policyname;
```

Contrastar contra la tabla de inventario esperado. **Si aparece una tabla live sin RLS que no
está en la lista de la migración → añadirla a la migración ANTES de aplicar** (aún no está
aplicada; tras aplicarse, cualquier extensión es migración nueva). Guardar el output íntegro:
es el receipt de estado-previo que fija el rollback (el fichero de rollback se ajusta contra él
si difiere del esperado).

### Paso 2 — Aplicar la migración

Con el visto de Alberto: ejecutar `supabase/migrations/20260722120000_s278_rls_hardening.sql`
(SQL Editor o CLI). La migración es una transacción con pre/postcondiciones que abortan y
revierten sola si el estado no cuadra (`lock_timeout 5s` — si aborta por lock, reintentar, no
forzar). Registrar: timestamp, quién la aplicó y SHA-256 del fichero aplicado
(`Get-FileHash -Algorithm SHA256`). El `NOTIFY pgrst, 'reload schema'` va dentro.

### Paso 3 — Smoke del bot (invarianza service_role; ~$0.10-0.30)

```
python -m pytest -q                    # suite verde (sin red)
python -m scripts.smoke_test --quick   # 3 queries por el seam servido real
```

Esperado: idéntico a pre-migración (retrieve → rerank → coverage → generate con respuestas
no-vacías; el smoke imprime receipt de coverage). Verificar además que el logging escribe
(`query_logs` recibe la fila del smoke si se pasa por el bot, o al menos que ninguna llamada
Supabase del pipeline devuelve error de permisos). Cualquier desviación → paso 5 no se estampa
y se evalúa rollback (`supabase/rollbacks/20260722120000_s278_rls_hardening.sql` — restaura la
EXPOSICIÓN: solo con visto explícito).

### Paso 4 — Verificar Advisor

Re-correr el Security Advisor de Supabase. Esperado: desaparecen los findings de RLS
deshabilitado sobre las tablas de la lista y los de grants sobre `chunks_v2_enunciados` /
`create_hnsw_index()`. Documentar los findings residuales (si los hay) con disposición
explícita (aceptado / migración futura). Si el Advisor aún reporta una exposición de las
CONFIRMADAS → el gate NO cierra; investigar antes de seguir.

### Paso 5 — Estampar receipt

Apendizar a `docs/DECISIONS.md` (decisión de sesión) y marcar TECH_DEBT #29 como cerrado-por-gate
con: SHA-256 y timestamp de la migración aplicada, output del inventario del paso 1 (pre) y su
re-run (post), resultado del smoke (paso 3) y del Advisor (paso 4), y el residual p1_readonly
declarado. Sin receipt completo el gate NO se declara cerrado (Protocolo 1: la verificación se
cita en el mismo turno que el "hecho").
