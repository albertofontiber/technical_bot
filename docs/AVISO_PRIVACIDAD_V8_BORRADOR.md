# AVISO DE PRIVACIDAD v8 — TEXTO FINAL, pendiente SÓLO de abogado (s324e)

> ⚠️ **Las 6 decisiones [DECIDIR] están RESUELTAS por Alberto (17-ago-2026, s324e).** Lo que queda antes de
> desplegar es **una sola cosa**: (1) ~~decisiones de Alberto~~ ✅ · (2) **revisión de abogado** — esto lo preparó un
> asistente de ingeniería, no una asesoría jurídica · (3) al desplegar, el bump v7→v8 exige **re-aceptación de TODOS
> los usuarios** (el gate de consentimiento es por versión, diseño s295). **Coste de la re-aceptación HOY: 1 usuario
> (Alberto)** — verificado en `answer_feedback`/`query_logs`: 96 consultas, un solo `telegram_user_id`. Ese coste
> crece con cada usuario que entre, así que el momento barato de hacer el bump es ANTES de abrir el piloto.
>
> **Por qué existe**: el v8 estaba reservado para el cambio de base jurídica (residuo RGPD del PLAN); abrir el bot a
> Directores Generales lo convierte en necesario también por el claim de cobertura (el v7 dice 3 marcas; el corpus
> tiene **30 fabricantes** con documentos activos — verificado hoy).

## Decisiones, resueltas

| # | Decisión | Resolución de Alberto (17-ago) |
|---|---|---|
| D1 | Base jurídica | **CONSENTIMIENTO** (se mantiene el de v7; ya implementado y revocable) |
| D2 | Retención | **24 meses** vinculado + disociación después (igual que v7) |
| D3 | Claim de cobertura | «**más de 30 fabricantes en general, no sólo PCI**». ⚠️ **Ajuste del autor**: el dato real hoy es **30 exactos** (docs activos, verificado 17-ago) ⇒ el texto dice «**una treintena de fabricantes**», que es verdadero hoy y estable si el número sube o baja. «Más de 30» sería falso por uno |
| D4 | Usuarios de otras compañías | **Cláusula explícita**: el responsable es Fontiber, no la empresa del usuario |
| D5 | Reconocimiento por feedback | **Aplica a todo el mundo** (Alberto: «lo utilizarán sólo empleados») |
| D6 | Banner beta | **Sí**, y además decir explícitamente que **está en desarrollo** + que no sustituye al manual oficial ni al criterio de un técnico cualificado |

---

## TEXTO 1 — `_CONSENT_TERMS` v8 (lo que ve el usuario en `/start`)

```
🤖 *Asistente técnico* — _versión beta, en desarrollo_

Te doy información extraída de los manuales técnicos de *una treintena de fabricantes*
(Notifier, Morley, Detnov, Kidde, Aritech, System Sensor y más). Puedes preguntarme por
texto o por audio 🎤.

⚠️ *Esto está EN DESARROLLO*: puede equivocarse o quedarse corto. Mis respuestas *no
sustituyen al manual oficial ni al criterio de un técnico cualificado* — contrástalas
antes de usarlas en una instalación. Si algo no cuadra, dímelo con 👎: es la forma más
rápida de mejorarlo.

⚠️ *Antes de empezar*

Para mejorar el sistema, guardamos *las preguntas que respondo y mis respuestas*, junto
con tu ID de Telegram, el nombre que nos des al aceptar y tus valoraciones 👍/👎. Si
mandas un audio, guardamos solo su transcripción: el audio original NO se guarda.

*Quién responde de tus datos*: *Fontiber Industrial Partners, S.L.* — también si trabajas
en otra empresa del grupo: el responsable es Fontiber, no tu empresa.
*Cuánto*: 24 meses vinculado a ti; después se retira tu identificador de tus consultas y
valoraciones.
*Quién lo ve*: el equipo técnico de Fontiber. Para funcionar, tus preguntas pasan por
proveedores de IA y de alojamiento que operan *fuera de la UE*.
*Tus derechos*: escribe a *info@fontiber.com* para acceder o borrar tus datos.

📄 Detalle completo (qué proveedores, para qué, y qué pasa a los 24 meses): /privacidad

Para aceptar y empezar, envía:
`/accept [tu nombre]`  _(el nombre es opcional pero ayuda a la revisión)_
```

**Notas de redacción (para el abogado):**
- Base jurídica = **consentimiento**, el que se da con `/accept` (D1). Se mantiene la revocación por correo.
- La frase de responsable cubre D4 sin meter jerga: dice quién responde y desmiente la suposición natural
  («esto lo trata mi empresa»).
- «una treintena de fabricantes» + ejemplos: cubre D3 sin lista cerrada que caduque (fue el error de v7) y sin
  afirmar un número falso.
- El bloque «EN DESARROLLO» cubre D6 y está **antes** del bloque de datos a propósito: es lo que más protege a un
  técnico que vaya a usar una respuesta en una instalación real.
- **Infra-promete a propósito** en lo que se guarda (decimos lo mismo o menos que v7), que es el lado seguro.

## TEXTO 2 — añadido a `_PRIVACY_DETAIL` (`/privacidad`)

Se mantiene íntegro el v7 y se añaden/ajustan estos tres puntos:

```
*Responsable*: Fontiber Industrial Partners, S.L. · CIF B24984759 · Calle de la Palma 10,
28004 Madrid · info@fontiber.com — Fontiber es el responsable del tratamiento aunque
trabajes en otra empresa del grupo.

*Base jurídica*: tu consentimiento, el que das al enviar /accept. Puedes retirarlo cuando
quieras escribiendo a info@fontiber.com; retirarlo no afecta a los tratamientos ya hechos.

*Reconocimiento*: si tu feedback ayuda a mejorar el sistema, Fontiber puede reconocerlo
internamente. Aplica a todas las personas que usen el asistente.
```

## Cableado (pendiente, NO hecho aquí)

1. `src/logging_db.py`: `TERMS_VERSION = "v8"` — el gate por versión invalida los consentimientos v7 y pide
   re-aceptación automáticamente (diseño s295, ya existente: no hay que tocar la lógica).
2. `src/bot/telegram_bot.py`: sustituir `_CONSENT_TERMS` y los tres puntos de `_PRIVACY_DETAIL`. El comentario
   in-situ que dice «cambiar esto exige bump a v8» debe actualizarse a v9 con el mismo criterio.
3. Test: el que pinea el sha256 del texto de consentimiento hay que actualizarlo **en el mismo commit** (es el
   guardarraíl que impide cambiar el aviso sin querer; buscar por `_CONSENT_TERMS` en `tests/`).
4. Smoke tras desplegar: `/start` en un cliente real debe mostrar el v8 y exigir `/accept` de nuevo.

## Riesgos declarados

1. **Sin revisión de abogado esto no se despliega.** Es el único bloqueante que queda y no es técnico.
2. El bump **corta el acceso a todo usuario existente** hasta que re-acepte. Hoy es 1 persona; si se despliega con
   el piloto en marcha, todos los DGs tendrán que volver a aceptar.
3. «Una treintena» es verdad con el corpus de hoy (30 exactos). Si se retiran documentos de un fabricante entero, el
   número baja — conviene re-verificarlo antes de cada cambio del aviso, no darlo por estable para siempre.
4. El texto no menciona que las respuestas puedan citar documentos de fabricantes no anunciados nominalmente; con
   «una treintena» + ejemplos queda cubierto, pero es una decisión de redacción, no una garantía jurídica.
