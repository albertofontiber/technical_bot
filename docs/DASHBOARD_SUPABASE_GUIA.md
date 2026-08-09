# Guía: montar el panel de KPIs en Supabase (10 minutos, sin código)

> **Para quién.** Alberto. **Por qué así.** DEC-183 (s301): «dashboard SIN app» —
> el lado servidor ya está construido y VIVO (vistas versionadas + `rag_trace`);
> el front son clicks en el dashboard de Supabase. Un panel web propio sería
> cambio de rumbo (auth + RGPD) y hoy no paga.
>
> **Estado verificado (s315, 9-ago-2026, contra la DB real):** las 6 vistas
> existen y tienen datos. La 7ª (latencia por etapa) llega con la migración s315.

## Las vistas y qué pregunta responde cada una

| Vista | Pregunta que responde | Filas hoy |
|---|---|---|
| `bot_health_daily` | ¿Cuántas consultas/día, de quién (seudónimo), latencia p50/p95? | 32 |
| `bot_health_semanal` | Lo mismo agregado por semana (tendencia) | 13 |
| `bot_uso_por_canal` | ¿Por qué canal entra el uso (texto/voz) y qué rutas (rag/clarify/shortcuts)? | 14 |
| `bot_feedback_semanal` | 👍/👎 por semana | 2 |
| `bot_motivos_negativos` | Motivos del 👎 (botonera) + la prosa con intención explícita | 3 |
| `salud_canal_retrieval_v1` | ¿Cuántos turnos respondieron con el pool DEGRADADO y qué canal falló? | 22 |
| `salud_latencia_etapas_v1` (s315, tras migración) | ¿Dónde se van los 34s? (retrieve/rerank/coverage/generate/resto, p50 diario) | — |

Sobre «quién pregunta»: por RGPD (s295-s299) las vistas trabajan con **seudónimo
estable**, no con identidad. Marcas y tipos de pregunta viven en `query_logs`
(`product_models`, `route`) — la consulta ad-hoc de abajo las agrega.

## Montaje (opción A — Reports con gráficos, recomendada)

1. Entra en el proyecto `technical-bot` → menú izquierdo **Reports** → **New report**
   (nómbralo `Bot PCI — KPIs`).
2. **Add block → Chart**. En el editor SQL del bloque pega, por ejemplo:
   `select dia, consultas from bot_health_daily order by dia;`
   → tipo *Bar/Line*, eje X `dia`, eje Y `consultas`. Guarda.
3. Repite un bloque por vista (un `select * from <vista> order by 1 desc;` como
   tabla también vale — no todo necesita gráfico).
4. Bloque extra «marcas consultadas» (ad-hoc, no hay vista dedicada):
   ```sql
   select unnest(product_models) as modelo, count(*) as veces
   from query_logs where created_at > now() - interval '90 days'
   group by 1 order by 2 desc limit 20;
   ```
5. El report queda guardado en el proyecto: volver a verlo = 1 click.

## Montaje (opción B — SQL Editor con snippets guardados)

Si Reports no te convence: **SQL Editor** → pega `select * from <vista>` → **Save
query** con nombre (`KPI · salud diaria`, etc.). Quedan en la barra lateral,
compartidos con cualquier miembro del proyecto.

## Notas

- Las vistas son `security_invoker` y SIN grant a `anon`/`authenticated` (lección
  s299/s301): solo se ven desde el dashboard de Supabase (service) — no hay
  superficie pública nueva.
- Si una vista sale vacía un día no es un fallo: es que ese día no hubo tráfico
  de esa clase (p.ej. `bot_motivos_negativos` solo crece con 👎).
- `salud_latencia_etapas_v1` distingue «sin medida» de «rápido»: las filas
  anteriores al deploy s315 cuentan en `turnos_rag` pero no en
  `turnos_con_medida` (patrón s306).
