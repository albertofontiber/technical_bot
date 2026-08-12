# AVISO DE PRIVACIDAD v8 — BORRADOR (s319)

> ⛔ **BORRADOR — NO DESPLEGAR.** Este texto NO sustituye al v7 servido por el bot.
> Requisitos antes de desplegar: (1) decisiones [DECIDIR] de Alberto resueltas;
> (2) **revisión de abogado** (esto lo preparó un asistente de ingeniería, no una
> asesoría jurídica); (3) el bump v7→v8 exige **re-aceptación de TODOS los usuarios**
> (el gate de consentimiento es por versión — diseño s295, deliberado).
>
> **Por qué existe**: el v8 estaba reservado para el cambio de base jurídica (residuo
> RGPD del PLAN); abrir el bot a Directores Generales de otras compañías lo convierte
> en necesario también por el claim de cobertura (el v7 dice 3 marcas; el corpus tiene
> 30 fabricantes — infra-prometer era el lado seguro, pero es mala carta ante un DG).

## Decisiones que bloquean el texto final

| # | Decisión | Opciones (mi lectura, para el abogado) |
|---|---|---|
| D1 | **Base jurídica** | (a) seguir en CONSENTIMIENTO (simple, ya implementado, revocable por mail) · (b) INTERÉS LEGÍTIMO para la telemetría de mejora + consentimiento solo para lo identificativo (menos re-aceptaciones futuras; exige test de ponderación documentado — abogado) |
| D2 | **Retención** | v7 = 24 meses vinculado + disociación después. ¿Se mantiene para externos? |
| D3 | **Claim de cobertura** | (a) «manuales técnicos de más de 30 fabricantes de PCI» (recomendada: verdadera y estable) · (b) lista literal (se queda stale — es lo que pasó) |
| D4 | **Usuarios de otras compañías** | El responsable sigue siendo Fontiber; propongo cláusula explícita: «puedes usar el bot como profesional de otra empresa; tus datos los trata Fontiber como responsable, no tu empleador». ¿El abogado ve necesidad de acuerdo con la compañía del DG? |
| D5 | **Reconocimiento de aportaciones** | La cláusula v7 (incentivos por feedback útil) ¿aplica a externos o se acota a técnicos internos? |
| D6 | **Banner beta** | Mantener «versión beta» + añadir «las respuestas no sustituyen al manual oficial ni al criterio de un técnico cualificado» (alineado con #71: el bot cita manuales, no asume responsabilidad) |

## CAPA 1 — borrador (lo que se ve antes de aceptar)

> 🤖 *Asistente técnico PCI* — _versión beta_
>
> Te doy información de los manuales técnicos oficiales de **más de 30 fabricantes**
> de protección contra incendios [D3]. Puedes preguntarme por texto o por audio 🎤.
>
> ⚠️ *Antes de empezar*
>
> Para mejorar el sistema, guardamos *las preguntas que respondo y mis respuestas*,
> junto con tu ID de Telegram, el nombre que nos des al aceptar y tus valoraciones
> 👍/👎. Si mandas un audio, guardamos solo su transcripción: el audio original NO
> se guarda.
>
> *Cuánto*: [D2 — v7: 24 meses vinculado a ti; después se retira tu identificador].
> *Quién lo ve*: el equipo técnico de Fontiber. Para funcionar, tus preguntas pasan
> por proveedores de IA y de alojamiento que operan *fuera de la UE*.
> *Si usas el bot como profesional de otra empresa*: tus datos los trata Fontiber
> como responsable; tu empleador no accede a tus consultas [D4].
> *Tus derechos*: escribe a *info@fontiber.com* para acceder o borrar tus datos.
>
> ℹ️ Las respuestas citan los manuales oficiales, pero no los sustituyen ni
> reemplazan el criterio de un técnico cualificado [D6].
>
> 📄 Detalle completo: /privacidad
>
> Para aceptar y empezar, envía: `/accept [tu nombre]`

## CAPA 2 — cambios sobre el /privacidad v7 (solo los diffs)

1. **Base jurídica**: [D1 — si (b), redacción del abogado; si (a), sin cambio].
2. **Cobertura**: misma corrección [D3] en cualquier mención.
3. **Cláusula de profesional externo** [D4]: nueva, tras «Quién accede».
4. **Reconocimiento de aportaciones** [D5]: mantener / acotar «a técnicos del grupo
   Fontiber» según decisión.
5. **Advertencia de uso** [D6]: nueva línea en «Para qué».
6. Sin cambios en: destinatarios por categoría (diseño correcto), derechos,
   transferencias, reclamación AEPD, retirada de consentimiento.

## Mecánica del despliegue (cuando el abogado dé el OK)

- Bump `TERMS_VERSION` v7→v8 en `telegram_bot.py` → TODOS los usuarios existentes
  ven el aviso de nuevo y re-aceptan (gate por versión ya construido, s295).
- La fila de `user_consent` conserva la versión aceptada — la prueba de qué texto
  aceptó cada quién sobrevive al bump.
- El texto v7 NO se edita nunca retroactivamente (es lo que la gente aceptó).
