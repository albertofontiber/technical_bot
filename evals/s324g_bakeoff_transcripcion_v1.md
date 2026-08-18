# s324g — Bake-off de transcripción: el problema NO era el prompt, era el modelo

> Recibo de `scripts/s324g_bakeoff_transcripcion.py` · 18-ago-2026 · coste ≈ 0,10 $ ·
> prompt de vocabulario INTACTO (el mismo para los tres brazos) · voz sintética (gap declarado).

## El disparador

Alberto, sobre el parche de «Death Knob» → «Detnov»: *«ahora traduce Detnov como Death Knife, y da
error. La solución de Death Knob me parece un parche […] además, esto será un problema frecuente ya
que los técnicos no saben inglés»*. Tiene razón en las tres cosas:

1. **Es reactivo**: la tabla cubre lo visto y falla con la variante siguiente **del mismo nombre**.
2. **Aunque la corrección acierte, el técnico ve su pregunta mal transcrita** — y eso hunde la
   confianza igual que una respuesta mala.
3. **Va a ser frecuente**: los técnicos hablan español y las marcas son anglosajonas o inventadas.

## El dato

Ocho frases del dominio, con la marca en el sujeto (si se pierde, el turno se queda sin ancla).
Mismo audio y mismo prompt para los tres modelos.

| modelo | marca bien transcrita |
|---|---|
| **`whisper-1`** — el que usa producción, y el default del código | **4 / 8** |
| `gpt-4o-mini-transcribe-2025-12-15` | **7 / 8** |
| `gpt-4o-transcribe` | **7 / 8** |

Los fallos de `whisper-1` son exactamente la clase que se sufrió en el piloto:

| dicho | `whisper-1` transcribió |
|---|---|
| «…de la CAD 250 de **Detnov**» | «…de la K-250 de **DETHNOS**» |
| «…centrales de **Aritech**» | «…centrales de **ARITEC**» |
| «…documentación de **Xtralis**» | «…documentación de **X-TRALIS**» |
| «…centrales de **Kidde**» | «…centrales de **KIDE**» |

**Los tres modelos fallan con «Kidde»** — en español suena «qui-de» y ninguno lo recupera. Ése es
el residuo real, y es donde una red de corrección sí tiene sentido.

## Qué invalida esto

- **La hipótesis «hay que pulir el prompt» queda descartada por medición.** El prompt es idéntico
  en los tres brazos y la diferencia es 4 vs 7: lo que cambia el resultado es el MODELO. Encaja con
  lo ya medido en s324f: «Detnov» **ya estaba** en el prompt y `whisper-1` lo destrozaba igual.
- **La hipótesis «hay que cambiar de interfaz de voz» es prematura.** No hace falta salir de
  OpenAI: el propio proveedor tiene modelos nuevos, ya declarados en `src/config.py` como brazos
  reversibles, y nunca se habían probado.
- **Mi tabla de confusiones deja de ser la solución** y pasa a ser, como mucho, red para el residuo.

## Gaps declarados

1. **La voz es SINTÉTICA.** Un técnico en obra tiene acento, prisa y ruido. Esto ordena candidatos;
   **no promete una tasa en campo**. El testigo real sigue siendo un audio humano — y es lo que hay
   que hacer antes de dar el cambio por bueno.
2. **El criterio de acierto es «la transcripción CONTIENE la marca»**, que es laxo: `mini` escribió
   «Extralis» y cuenta como acierto, mientras `gpt-4o-transcribe` escribió «Xtralis» exacto. Por eso
   el empate 7/7 no es un empate real en calidad.
3. **8 frases y 8 marcas** de 30. No es la distribución de uso real.
4. **Coste por minuto**: `gpt-4o-transcribe` ≈ el de `whisper-1`; `mini` es más barato. Con audios
   de segundos, la diferencia es despreciable frente al fallo que evita.

## Recomendación

1. **`VOICE_TRANSCRIPTION_MODEL=gpt-4o-transcribe` en Railway.** Es una variable de entorno, ya
   validada por el código contra una lista cerrada, y **reversible al instante** — no hay que
   desplegar nada. El brazo `mini` queda como alternativa si el coste importara.
2. **Confirmar con un audio humano** (Alberto preguntando por Detnov y por Kidde) antes de darlo
   por bueno. Sin eso, esto es una medición de laboratorio.
3. **Sustituir la tabla de parches por algo estructural** para el residuo tipo «Kidde»: mapear lo
   transcrito contra las **30 marcas reales** —que ya se derivan de la base— por proximidad
   fonética, en vez de mantener una lista de errores vistos. Eso cubre «KIDE», «Key de», «qué de»…
   de una vez, sin ir por detrás de cada variante nueva. Va con dúo: toca serving y puede corregir
   de más.
