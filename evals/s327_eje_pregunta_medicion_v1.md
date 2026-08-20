# s327 — El eje `es_pregunta`: medición de calidad (censo, no muestra)

> **Por qué existe**: el dúo (Sol, s327) señaló que los recibos del job prueban EJECUCIÓN
> —109/109, 0 fallos, coste— pero no CALIDAD, y que la pregunta central del eje es si deja
> fuera del análisis alguna pregunta real. Esto lo mide.
>
> **Cómo se mide**: censo COMPLETO de los casos auditables, no una muestra. De las 109 filas,
> **93 las resuelve la regla determinista** (terminan en «?») y no admiten error de criterio:
> quedan **16 casos** donde alguien decidió —el LLM— y se revisan uno a uno.
>
> **Nota de proceso (hallazgo crítico F1 de Fable, s327)**: el briefing del dúo CITÓ este fichero
> antes de que existiera. El censo se había hecho, pero el artefacto no estaba versionado cuando
> el revisor fue a abrirlo — y un cierre anclado a algo que el revisor no puede leer no es una
> verificación. De ahí el bloque «Recibo» del final: las cifras de abajo NO salen de mi memoria,
> salen de una consulta a la base de PRODUCCIÓN, reproducible.
>
> **Vara**: el error que importa es el **falso negativo** (una pregunta real marcada como
> no-pregunta ⇒ desaparece del análisis). El falso positivo es el error que el diseño ELIGE
> («ante la duda, pregunta», adjudicación de Alberto).

## Los 16 casos que decidió el modelo (taxonomía v8)

### 9 marcadas PREGUNTA sin terminar en «?»

| # | Mensaje | Veredicto |
|---|---|---|
| 1 | «Especificaciones técnicas de la central NFS2-3030» | ✅ pide un dato |
| 2 | «Procedimiento de instalación de un lazo Morley» | ✅ |
| 3 | «Especificaciones del detector DGD-600» | ✅ |
| 4 | «Características de la AFP-200E» | ✅ |
| 5 | «esquema de conexión del CAD-250» | ✅ |
| 6 | «sus especificaciones técnicas básicas» | ✅ continuación que SÍ pide |
| 7 | «creo que también tenemos información sobre el ASD535» | ⚠️ afirmación, no petición — **falso positivo tolerado** |
| 8 | «Me has pasado información sobre la ID3000 que no es de Detnov…» | ⚠️ queja con petición implícita («quería la de Detnov») |
| 9 | «Te he pedido información sobre centrales analógicas…» | ⚠️ ídem |

### 7 marcadas NO-PREGUNTA

| # | Mensaje | Veredicto |
|---|---|---|
| 1 | «ok, entendido» | ✅ acuse |
| 2 | «Programación principalmente.» | ✅ continuación |
| 3 | «Sobre la 2X-AF1-FBS.» | ✅ continuación |
| 4 | «estoy trabajando con la ZX1e» | ✅ contexto, no petición |
| 5 | «esto parece incluir muchos más productos que "centrales de incendios"» | ✅ feedback |
| 6 | «sonda-018» | ✅ es una sonda de prueba, no un técnico |
| 7 | «ZX1e» | ⚠️ **el único falso negativo posible**: si fue la respuesta a una clarify, era parte de una petición |

## Resultado

| Métrica | Valor |
|---|---|
| Resueltas por regla determinista (sin criterio) | **93 / 109 (85 %)** |
| Decididas por el modelo | 16 |
| **Falsos negativos** (pregunta real excluida del análisis) | **≤ 1 / 109 = 0,9 %** — «ZX1e», dudoso |
| Falsos positivos (no-pregunta contada como pregunta) | 3 / 109 = 2,8 % — el error que el sesgo ELIGE |

**Lectura honesta**: el eje cumple lo que se le pidió —no perder preguntas— con un único caso
dudoso, y ese caso es **exactamente** el gap ya declarado en TECH_DEBT #92: el clasificador no
ve el hilo, así que un modelo suelto respondiendo a una clarify le resulta indistinguible de un
mensaje sin petición. No se tuneó el prompt para ganarlo: se declara.

**Límite de esta medición**: es un censo del histórico PRE-piloto (109 mensajes, 2 personas,
muy pocas conversaciones multi-turno). La proporción de continuaciones subirá con tráfico real
y con ella el peso del gap #92. Re-medir con los primeros ~200 mensajes del piloto.

## Recibo — verificación contra producción (20-ago-2026)

Las cifras de arriba no se sostienen en la lectura del job: se re-derivan de la base. La consulta
replica en SQL la MISMA regla que el código (`rtrim` del conjunto de cierres que
`_CIERRES_TRAS_INTERROGACION` recorta, y luego `?`/`？` al final):

```sql
SELECT COUNT(*) AS filas,
       COUNT(*) FILTER (WHERE rtrim(btrim(l.query), E' \t\r\n"''»)]}.…') LIKE '%?'
                           OR rtrim(btrim(l.query), E' \t\r\n"''»)]}.…') LIKE '%？')
                                                   AS termina_interrogacion,
       COUNT(*) FILTER (WHERE c.es_pregunta)       AS es_pregunta_true,
       COUNT(*) FILTER (WHERE NOT c.es_pregunta)   AS es_pregunta_false,
       COUNT(*) FILTER (WHERE c.query_log_id IS NULL) AS sin_clasificar,
       MIN(c.taxonomia_version), MAX(c.taxonomia_version)
  FROM query_logs l
  LEFT JOIN query_clasificacion c ON c.query_log_id = l.id;
```

| filas | termina_interrogacion | es_pregunta=true | =false | sin_clasificar | versión mín/máx |
|---|---|---|---|---|---|
| 109 | **93** | 102 | 7 | **0** | **8 / 8** |

Y las tres comprobaciones que cierran el censo:

- **93** confirma el 85 % que resuelve la regla determinista, sin criterio de nadie.
- **102 − 93 = 9** = las 9 filas marcadas PREGUNTA sin terminar en «?» → la primera tabla.
- **7** = las marcadas NO-PREGUNTA → la segunda tabla. **9 + 7 = 16 casos auditables**, que es
  el censo entero: no queda ninguna decisión del modelo fuera de esta revisión.

`sin_clasificar = 0` y `taxonomia_version` mín = máx = 8 cierran la otra mitad: no hay filas
pendientes ni mezcla de versiones, así que el censo mira exactamente el estado vigente.
