# Diseño del lever de SÍNTESIS (Fase 2 s44) — DRAFT para sign-off G3

> **⚠️ PARQUEADO (s44, tras el A/B de fetch-ancho):** los dos casos que anclaban este
> diseño —hp020 (over-admit) y hp001 (multi-doc)— **MEJORARON con retrieve-wide (15→50)**:
> eran retrieval-contexto, no síntesis pura (el chunk estaba en top-5 pero el contexto de
> soporte no, y entraba ruido). El "chunk en top-5 = síntesis" del funnel era demasiado
> grueso. → El target real de síntesis es **lo que QUEDE como FALLO tras el fetch-ancho**,
> pendiente de la confirmación K-mayoría. Si queda poco/nada, este lever no se necesita.
> NO cablear nada de aquí hasta re-anclar el target con los casos residuales reales.

> **Caveat (DEC-001):** generación tiene mal historial — change-1 (error simétrico) = direccional+ pero medido vs ruler roto; change-2 (completitud) = REVERTIDO net-negativo. Esto es un DRAFT para tu G3, no para cablear sin tu OK. Anclado en los casos REALES del bulto (`_s44_synthesis_cases.txt`), no en abstracto.

## Hallazgo clave: SÍNTESIS NO es un solo lever — son ≥2 modos distintos

| caso | modo | evidencia (bot real) | retrieval ok? |
|---|---|---|---|
| **hp020** | **OVER-ADMIT** | dio Nivel-2 completo citando [F1]=HOP-138; luego "los fragmentos no incluyen procedimiento de Nivel 3" — el gold dice **mismo flujo** con sesión Nivel-3. Se negó a extender. | **SÍ** (HOP-138 en sources) → síntesis pura |
| **hp001** | **MULTI-DOC wrong-source** | citó "clave 1111 [F3]" del manual de USUARIO (MU-376) para acceso AVANZADO; se necesita admin 2222 (MC-380). Tenía AMBOS. | sí (MC-380 + MU-376 en sources) |
| hp005/11 | contradicción de valor | (s43: da valor equivocado) — re-caracterizar tras A/B retrieval | TBD |
| hp008 | omisión (core 0/4) | (s43: no extrae) — TBD | TBD |

→ **No puedo prometer "un lever de síntesis arregla el bulto".** Hay al menos: (A) over-admit, (B) multi-doc, (C) omisión. Cada uno = fix distinto + medición propia.

## Diagnóstico del mecanismo (A = over-admit, el más claro)

El `SYSTEM_PROMPT` del generador (`generator.py:16-158`) es **brutalmente asimétrico**: ~100 líneas de CERO INVENCIÓN + 8 anti-ejemplos + "si no puedes citar [F<n>], BÓRRALO" + "antes de enviar, revisa que cada dato esté LITERALMENTE en un fragmento". **Cero contrapeso** para "usa el dato que SÍ está / infiere la extensión directa". El bot, primado a admitir, dice "no especifica Nivel 3" aunque el flujo esté en [F1]. = el "error simétrico" de change-1: **rechazar-en-falso con el dato presente es hermano de inventar.**

## Levers candidatos (por modo, escalonados)

**Modo A (over-admit) — RE-TEST de change-1 sobre el ruler ACTUAL (mejor que el s30 roto):**
Bloque corto y calibrado: *"Es tan grave NO usar un dato presente en un fragmento como inventar uno ausente. Si el dato está en un [F<n>], úsalo con confianza. Si un procedimiento citado aplica a una variante mencionada (p.ej. mismo flujo para Nivel 2 y Nivel 3), dilo explícitamente. Antes de escribir 'el manual no especifica X', verifica que NINGÚN fragmento lo contiene ni se deduce directamente de uno."*
- **Por qué este primero:** cambio de prompt acotado, history-backed (direccional+ en s30), ataca el mecanismo raíz (asimetría).
- **RIESGO (DEC-001):** relajar la cautela puede **subir alucinación**. Mitigación = el A/B mide **DOS EJES**: over-admit ↓ **Y** el eje no-fabricación/invención NO ↑ (el eje de s41/DEC-012 ya está en el árbitro). Vara = bajar FALLO de over-admit **a invención igual o menor**. Si sube invención → revertir (como change-2).

**Modo B (multi-doc wrong-source):**
Guía de desambiguación: *"Si fragmentos de manuales DISTINTOS del mismo producto dan valores distintos para lo mismo (clave usuario vs admin, valor por revisión), razona cuál aplica a la TAREA preguntada y cita ese; no des el primero que aparezca."*
- Medir aparte (no bundlear con A — contamina, lección #2-desbundle DEC-016).

**Descartado de entrada:** structured-extraction / two-pass de completitud = territorio change-2 (REVERTIDO, net-negativo, más invasivo + más latencia). NO empezar por ahí.

## Medición (K-mayoría, escalonada, ambos ejes)
1. Fase 1 (retrieval) primero **reduce el bulto** → los que queden con el chunk en top-5 = síntesis pura = el target real. hp020 ya es target seguro; hp001 también.
2. A/B modo A: prompt actual vs +bloque-simétrico, K-mayoría sobre el target. Ejes: FALLO-over-admit ↓ + invención/no-fab no ↑.
3. Si A mueve sin coste → modo B aparte.

## Dependencia
Fase 1 (retrieval, corriendo) define el target de síntesis. Este diseño se FINALIZA cuando el A/B de retrieval diga qué casos quedan como síntesis pura. hp020/hp001 son target seguro ya.
