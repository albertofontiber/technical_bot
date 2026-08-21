# s332b · La invitación del aviso no tenía receptor — fix observado y verificado (21-ago-2026)

> Primera conversación real post-flip de s332 (Alberto, 10:40Z, ambas flags on,
> deploy `5951b64`). El nivel-aviso funcionó; su INVITACIÓN, no.

## Lo observado (query_logs, leído verbatim)

| id | turno | qué pasó |
|---|---|---|
| `322b4e0a` 10:40:22 (voz) | «¿Qué centrales ID tienes?» (Whisper volvió a destrozar «Kidde»→«ID») | **Conducta DISEÑADA**: respuesta de la familia ID intacta + asunción `{marca_asr, aviso, Kidde}` estampada (`asunciones.status=on, n=1` — primera fila con la sección viva en producción) + línea ℹ️ en la confirmación: «…Si dictaste Kidde, dímelo.» |
| `57b8d482` 10:40:29 (texto) | **«sí, dije Kidde»** — la respuesta natural a ESA invitación | **Plantilla vacía.** La red de corrección no disparó: el léxico no tenía el cue «decir»-en-pasado y la plantilla cerrada `^cue…$` no toleraba el «sí, » inicial. Clase R1 declarada en v2 §7 (léxico infra-cubre; crece por observación) — mordiendo en su primer día. |

## El fix (la vía de crecimiento pre-declarada, con cita)

1. **Léxico** (`config/correction_lexicon_v1.yaml`): + `dije` · `he dicho` · `i said`,
   con la cita `57b8d482` en el header — disciplina DEC-233 intacta (solo lo observado).
2. **Cabeza opcional en la plantilla** (`_correction_rebuild`): se admite UN token del
   léxico GOBERNADO de confirmación delante del cue — afirmación con separador libre
   («sí, dije Kidde», «sí dije Kidde»); negación SOLO con corte de cláusula `[,:]`
   (polaridad s331 desde `_NEGATION_CUES`): «no, dije Kidde» corrige; «no dije Kidde»
   y «no me refería a Kidde» siguen SIN disparar (los casos congelados pasan).
   El «no» pelado NO se añade al léxico de confirmación compartido — cambiaría la
   regla 3 de la gramática de pending (hoy «no» a secas = cambio de tema).

## Verificación

- Tests: 5 nuevos sobre el caso observado y sus polaridades; `test_s332_correccion_marca`
  29/29 + gramática de pending s331 intacta (37/37 juntos). Suite completa: (ver commit).
- **Replay e2e del hilo exacto**: T1 «¿Qué centrales ID tienes?» → T2 «sí, dije Kidde» ⇒
  `brand_correction_rebuild`, qfr = «¿Qué centrales ID tienes? (el usuario corrige: la
  marca es Kidde)», respuesta con **centrales Kidde Commercial** — sin plantilla vacía,
  sin cross-brand ID3000.

## Lo que queda declarado (sin construir)

- **El «sí» PELADO tras el aviso** (sin repetir la marca) sigue sin receptor: exigiría
  estado pendiente-de-aviso (patrón pending s331 aplicado al aviso ASR). Se diseña con
  su mini-gate si el tráfico lo observa — hoy la invitación dice «dímelo» y la
  respuesta observada trajo la marca.
- Whisper lleva 3/3 turnos de hoy convirtiendo «Kidde»→«ID» por voz: la fila
  aviso-ID acumula observaciones; su re-adjudicación (¿graduar el aviso a pregunta
  dirigida?) queda para el seguimiento con tráfico (R4).
