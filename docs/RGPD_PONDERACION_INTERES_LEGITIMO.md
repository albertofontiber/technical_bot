# Análisis de ponderación — interés legítimo (BORRADOR para validación legal)

> **Estado: BORRADOR SIN VALIDAR.** Lo redacta el asistente técnico del proyecto, que NO es
> asesor legal, para que quien lleve cumplimiento en Fontiber **revise y corrija** en lugar de
> producir desde cero. Nada de este documento surte efecto hasta esa validación. La decisión
> de cambiar la base jurídica es de Alberto con su asesor (pendiente 8 de
> `docs/RGPD_RETENCION.md`).

## 0. Qué se está decidiendo

Hoy el sistema opera sobre **consentimiento** (gate `/accept`). Este documento prepara el
cambio a **interés legítimo (art. 6.1.f RGPD)** como base para el tratamiento principal,
manteniendo el consentimiento explícito solo para lo que lo exija de verdad (p. ej. una futura
memoria durable opt-in, o el uso del material para entrenar un modelo propio).

Por qué se plantea: (a) para una herramienta de trabajo que la empresa pone al técnico, el
consentimiento es frágil — quien no puede negarse sin coste laboral no consiente libremente;
(b) con interés legítimo, un cambio del aviso se **informa** en lugar de re-aceptarse, lo que
elimina la fricción recurrente que hoy impone `TERMS_VERSION`.

## 1. El tratamiento

| | |
|---|---|
| Responsable | Fontiber Industrial Partners, S.L. · CIF B24984759 · Calle de la Palma 10, 28004 Madrid |
| Interesados | Técnicos de PCI que usan el bot de Telegram como herramienta de trabajo |
| Datos | Preguntas respondidas y sus respuestas; transcripción de audios (el original no se guarda); ID de Telegram; nombre dado al aceptar; valoraciones 👍/👎 con su motivo y explicación |
| Finalidades | (1) Operar el asistente; (2) diagnosticar errores y mejorar la calidad de las respuestas con uso real; (3) reconocer las aportaciones de feedback valiosas — con decisión final siempre humana |
| Encargados | Telegram (canal) · Anthropic (generación) · Voyage AI (búsqueda) · OpenAI (transcripción) · Supabase (almacenamiento, UE) · Railway (ejecución) |
| Plazo | 24 meses identificado → disociación (seudónimo estable; el vínculo se destruye) |

## 2. Juicio de idoneidad — ¿el interés es legítimo y real?

El interés: **mantener y mejorar una herramienta técnica de trabajo con el uso real de quienes
la usan**. Es lícito, concreto y actual — no especulativo: el ciclo pregunta→fallo→corrección
es el mecanismo documentado de mejora del sistema (evaluación con casos reales, corrección de
errores detectados por técnicos). Es además un interés **esperable** por el interesado: quien
usa una herramienta beta sabe que su uso la mejora, y así se le dice en el primer mensaje.

## 3. Juicio de necesidad — ¿hay vía menos intrusiva?

- **¿Datos sintéticos o de laboratorio?** No capturan los fallos reales (vocabulario de obra,
  equipos legacy, preguntas mal formuladas), que son exactamente lo que hay que corregir. Ya se
  probó: la evaluación de laboratorio no predijo los fallos orgánicos.
- **¿Menos datos?** Ya minimizado: el audio original no se conserva; los saludos y despedidas
  no se registran; los exports internos llevan seudónimo, no identificador; el log del proceso
  no recibe el texto de las preguntas.
- **¿Menos tiempo?** El plazo (24 meses) termina en disociación irreversible, no en archivo.

## 4. Ponderación — el interés frente a los derechos del técnico

**Impacto sobre el interesado: bajo.** Argumentos, cada uno anclado en un mecanismo real:

1. **Contexto laboral esperable**: los datos son consultas técnicas profesionales sobre equipos
   de incendios, no vida privada. Tratamiento dentro de la relación herramienta-trabajo.
2. **Sin perfilado oculto ni decisiones automatizadas**: la única evaluación sobre la persona
   (la marca de utilidad del feedback) la pone un revisor humano, es auditable contra
   artefactos reales (una corrección, un caso de evaluación, un manual adquirido), y cualquier
   decisión derivada (reconocimiento/incentivo) **la toma una persona** — el sistema no puede
   escribir esa marca desde el canal del bot (restricción estructural, no de política).
3. **Disociación con seudónimo a los 24 meses**, con destrucción del vínculo verificada contra
   base de datos real en integración continua.
4. **Transparencia en dos capas**: aviso corto antes de usar + `/privacidad` con el detalle
   completo, legible sin aceptar nada.
5. **Derechos operativos**: acceso/supresión por `info@fontiber.com` (procedimiento interno
   documentado), reclamación ante la AEPD declarada en el aviso.
6. **Evidencia**: libro de eventos de consentimiento de solo inserción (`consent_events`).

**Contrapesos honestos, declarados:**
- El texto libre puede contener datos personales incidentales (nombres, obras); por eso el
  resultado se llama seudonimización y no anonimización, y la supresión a petición incluye
  revisar la prosa.
- Cuatro encargados procesan fuera de la UE; el mecanismo de transferencia está **pendiente de
  documentar** (pendiente 6 de la matriz). El asesor debe cerrarlo antes de apoyarse en esta
  ponderación.
- El reconocimiento/incentivo introduce un interés del responsable en evaluar aportaciones;
  se mitiga con decisión humana + marca auditable, pero el asesor debe valorar si exige
  información adicional al trabajador por la vía laboral (representación, igualdad de trato).

**Conclusión provisional** (a validar): el interés es legítimo y real, no hay vía menos
intrusiva que sirva a la finalidad, y el impacto es bajo con las garantías vigentes ⇒ la
ponderación **favorece el interés legítimo** para las finalidades 1–3. Quedan FUERA y
exigirían consentimiento explícito propio: memoria durable de conversaciones (opt-in) y
entrenamiento de modelos propios con el material.

## 5. Derecho de oposición (art. 21)

Con interés legítimo, el técnico puede **oponerse** por su situación particular. Vía:
`info@fontiber.com`. Efecto: mismo mecanismo que la supresión/disociación a petición ya
documentado. El aviso deberá mencionarlo expresamente al cambiar de base.

## 6. Qué cambia si se aprueba

1. El gate `/accept` pasa de «consentir el tratamiento» a **acuse de recibo del aviso**
   (se conserva el gate y el libro de eventos: sirven como prueba de información).
2. El aviso (`/start` + `/privacidad`) declara interés legítimo como base, este análisis como
   respaldo, y el derecho de oposición.
3. Los cambios futuros del aviso se **informan** (mensaje del bot) en lugar de re-aceptarse;
   `TERMS_VERSION` pasa de tripwire de re-aceptación a tripwire de **re-información**.
4. Este documento se firma y se archiva con fecha; se revisa si cambia una finalidad.

## 7. Firma

- **Decidido por (Alberto):** ____________________ **Fecha:** __________
- **Validación legal (asesor/DPO):** ____________________ **Fecha:** __________
