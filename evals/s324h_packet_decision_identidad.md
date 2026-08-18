# Packet de decisión — ¿qué hace la voz cuando NO se puede verificar la marca?

**Para Alberto. Una casilla.** Es lo único que bloquea el cableado de s324h.

## Por qué aparece

Al pasar la voz por el plan, la voz empieza a ejecutar `_resolver_hechos`, que hoy
**no ejecuta nunca**. Esas consultas (`lookup_model_manufacturer`,
`manufacturer_in_db`) hacen `raise_for_status()`: un blip de Supabase **lanza**.

Hoy, con la voz fuera del plan, ese fallo no existe para el canal de voz: la pregunta
hablada se contesta por RAG igual. En cuanto la voz entre al plan, hay que decidir qué
pasa — y las tres salidas posibles tienen coste. Las dos primeras ya están medidas y
descartadas por el dúo; la tercera es alcance nuevo.

## Las tres salidas

| | Qué hace | Coste | Estado |
|---|---|---|---|
| **(a)** | Degradar al RAG, como si nada | **Riesgo cross-brand**: el bot puede contestar con el manual de OTRA central porque no pudo comprobar la identidad. En PCI eso es dar una especificación equivocada a alguien que está montando una instalación | **Descartada por Sol (r43)** — regresión de seguridad. Y Fable añadió que además borra la incidencia de `bot_errors`, o sea que ni te enteras |
| **(b)** | Dejar que la excepción suba: mensaje de error genérico, cero respuesta | La voz **pierde respuestas que hoy sí da**. Es lo que mi v3 hacía sin darse cuenta | **Descartada por Sol y Opus 5 (r44)**, los dos por separado — regresión para el canal que priorizaste |
| **(c)** | **Fail-closed honesto**: «No he podido comprobar de qué marca es esto ahora mismo. Vuelve a intentarlo en un momento.» | Alcance nuevo (texto + su test). Y el técnico no obtiene respuesta — pero sabe POR QUÉ y sabe que reintentar sirve | **Sin descartar. Es la que recomiendo** |

## Por qué recomiendo (c)

Las tres dejan al técnico sin la respuesta que quería. La diferencia es qué se lleva:

- con **(a)** se lleva una respuesta que puede ser de otra central, sin saberlo;
- con **(b)** se lleva un error genérico y no sabe si reintentar sirve de algo;
- con **(c)** se lleva la verdad y una acción útil.

Y hay un precedente tuyo de esta misma semana: el 429 de cuota. Ahí el bot decía
«estoy saturado, prueba en unos minutos» —dos cosas falsas— y lo arreglamos
distinguiendo el caso y diciendo la verdad. Esto es el mismo patrón: **no mentirle al
técnico sobre lo que puede hacer.**

## Lo que NO estoy proponiendo

No propongo tocar la conducta del canal de **texto**. Hoy, en texto, ese mismo fallo
sube al manejador de errores y genera incidencia en `bot_errors` — lo que s324e
construyó por tu incidente de cuota. Eso se queda **intacto**. Si (c) se aprueba, se
aplica sólo donde el problema nace: el canal de voz al entrar al plan.

Que texto y voz difieran aquí es una asimetría real y la declaro. Unificarlas también
es defendible, pero es una decisión mayor (toca la telemetría que acabamos de construir)
y no la meto de tapadillo en un lote de enrutado.

---

## Tu casilla

- [ ] **(c)** Fail-closed honesto en voz. Cableo s324h con esto y su fila en el gate.
- [ ] **(b)** Que suba el error. Más simple, y la voz pierde respuestas que hoy da.
- [ ] Otra cosa / hablarlo.

Sin esto, s324h no se cablea: es el único punto abierto que no puedo resolver midiendo.
