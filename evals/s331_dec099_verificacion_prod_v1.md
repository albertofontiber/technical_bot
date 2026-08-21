# s331 · Verificación DEC-099 EN PRODUCCIÓN (21-ago-2026, 07:50-07:53Z) — CERRADA ✅

> El paso final de DEC-257/258: Alberto repite la conversación del incidente del 18-ago en el
> bot REAL de Telegram, con las 4 flags encendidas (flip 07:37Z, deploy SUCCESS, interlock de
> boot pasado). Filas de `query_logs` con el trace `turn_identity` estampándose por primera vez
> en producción.

## El antes/después, turno a turno

| | 18-ago (incidente, 👎) | 21-ago (verificación) |
|---|---|---|
| **T1** «…la 2X-AF1-FBS» (VOZ, misma grafía ASR) | Bindeo truncado `['2X-AF1']` | `e70600ba…` 07:50:01 · **`models_provenance: resolved_this_turn`** — responde nombrando la **2X-AF1-FB-S** canónica y DECLARA ALCANCE: «No tengo la ficha del FB-S en los fragmentos; lo que sigue procede de la 2X-AF1-S, la variante sin controles de Bomberos… verifica» |
| **T2** «¿cómo la programo?» | **«¿Qué variante exacta del 2X-AF1 tienes instalada (mira la etiqueta del panel)…?»** | `70b0f02d…` 07:51:46 · **`carried`** — «"Programar" abarca varias cosas en la 2X-A: ¿lazo, zonas, E/S, grupos y retardos, o Día/Noche? ¿teclado o herramienta/PC?» — **cero re-pregunta de identidad** |
| **T3** «el lazo y sus dispositivos» | (nunca se llegó) | `5e018e62…` 07:53:37 · `carried` — **contenido del manual de FAMILIA**: hasta 128 dispositivos, protocolo Excellence, Clase A/B, 500 mA→800 mA [F1][F2], «aplica a la familia; ver nota sobre variantes» |

Los tres turnos con `turn_identity.status=on` y `presence=vigente` (la observabilidad B5 viva).
El residual T2-del-gate (confirmar-vs-declarar con evidencia de hermana) salió por la rama BUENA
en producción: alcance declarado + respuesta útil.

## Hallazgos COLATERALES de la misma mañana (07:45-07:48, conversación previa del catálogo)

1. **ASR destroza marcas (clase DEC-233, 2 observaciones NUEVAS)**: Alberto dijo «Kidde» por voz
   y Whisper transcribió **«BQide»** (07:45) y plausiblemente **«ID»** (07:47-48). El detector no
   falló — nunca vio «Kidde». Con «Detnov→Death Knob» (día 1 del piloto) ya son ≥3 filas
   observadas ⇒ **el fix diferido de DEC-233 (tabla de confusiones OBSERVADAS, consumida en
   `normalize_voice_query` con el ASR crudo siempre visible) tiene masa crítica para activarse.**
2. **Gap nuevo: corrección de MARCA sin estado** («me refería a Kidde» tras un turno sin
   producto): la cascada la trata como tema nuevo y el retrieval busca la meta-frase → plantilla
   vacía. Fix candidato: reconstruir la pregunta anterior (que `last_query` YA guarda) con la
   marca corregida — el mismo patrón que la corrección de producto. Diseño con mini-gate propio,
   pendiente de GO.

## Estado

- **DEC-099 de s331: VERIFICADA** — la clase amnésica del incidente está muerta en producción.
- Flags vivas en Railway worker (censo 07:37Z + sonda dirigida): las 4 s331 = `on`,
  `IDENTITY_RESOLVE=on`+`replace`. Rollback documentado: quitar las 4.
- Siguientes (no bloquean nada): tabla de confusiones ASR (GO pendiente) · corrección-de-marca
  (GO pendiente) · residuales post-flip de `s331_m4_gates_resultado_v1.md` (se observan con
  tráfico) · graduación de las 4 flags cuando asienten (patrón DEC-210/211).
