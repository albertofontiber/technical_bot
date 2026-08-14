# s321 E3 — Adenda al writer: split + atestación — v2 (dúo r25 aplicado)

> **v1→v2 (r25: Sol 4 · Fable 3 — crítico convergente: atestación ≠ sujeto):**
> 1. **Clase FORMA por la semántica del filtro, bidireccional** (Fable: la
>    raíz era normkey lossy, no la blacklist de signos): pm_prev matchea el
>    patrón imatch del canónico Y el canónico matchea el patrón de pm_prev
>    ⇒ solo forma. Sin enumeraciones.
> 2. **ATESTADA = SUJETO DOMINANTE, no mención** (Sol M1): el canónico debe
>    ser el token-producto DOMINANTE del contenido del doc (frecuencia vs
>    otros tokens de producto del catálogo en el mismo doc) — una mención de
>    compatibilidad/accesorio no atesta. Extractos muestreados al recibo.
> 3. **Evidencia CORRELACIONADA declarada** (Sol M2): doc_map s83 y el content
>    nacen del mismo manual — no hay «evidencia doble»; por eso el auto-apply
>    exige además las reglas 4-5 y todo lo demás lleva extractos al packet.
> 4. **pm_prev que sea PRODUCTO REAL (resoluble en catálogo o presente en el
>    snapshot del detector) → PACKET/multi-valor SIEMPRE** (Sol M3): perder un
>    término cruzado válido (`ID3000`→`NGU`) es pérdida de findability — la
>    decisión es multi-valor, jamás colapso automático.
> 5. **Sonda de HERMANAS sobre TODAS las aplicables** (Fable: SMART 3 →
>    smart-3g existe en clase 2): variantes hermanas del canónico presentes en
>    content ⇒ AMBIGUA ⇒ packet.
> 6. **Writer fail-closed en findability** (Sol M4): exit≠0 si cualquier
>    findability_post falla, no solo aborts CAS.
> 7. **Contabilidad del split cerrada** (Fable): cada pareja cae en EXACTAMENTE
>    un destino y la suma se asserta (la lección Fable-M3 de r24, aplicada al
>    split).

**Qué es**: refinamiento POST-r24, nacido del dry-run real (102 docs · 1.457
chunks · 99 parejas pm_prev→canónico). El dúo r24 validó el WRITER (T3, CAS,
findability); esta adenda decide QUÉ SUBCONJUNTO se aplica y con qué evidencia
— y no se ejecuta sin su propia ronda (pregunta de Alberto: «¿lo ha validado
el dúo?» — respuesta honesta: aún no; por eso este doc).

## El hallazgo del dry-run

Las 99 parejas NO son una clase homogénea:

1. **FORMA** (~9 parejas · ~149 chunks): normkey idéntico — solo ortografía
   (`RP-1002E`→`RP1002E`). Propuesta: aplicar sin más evidencia.
   Caveat ya cazado a mano: `SENTOX IDI`→`IDI+` parecía forma (normkey tira
   el «+») y es VARIANTE → clase 3. El criterio v1 (normkey==) tiene ese
   agujero de clase: signos con carga semántica (+, *, /).
2. **PM-BASURA** (~54 parejas · ~579 chunks): pm = artefacto de ingesta
   (`TO-60`, `FROM-01`, `EN-54-25`, `WEIGHT-96G`) → canónico adjudicado.
   Falsos conocidos del regex v1: `ART 535-x` (familia-x, no basura),
   `System 5000` (identidad). El regex NO es la evidencia — es un triage.
3. **IDENTIDAD REAL** (~35 parejas · ~680 chunks): estrechamientos a variante
   (`ASD533`→`ASD 533-1`, `FAAST`→`8100E`), familia→variante única
   (`ONE/ONE-LOOP`→`ONE 500` con manual «SERIE ONE»), nombres cruzados
   (`PA400`→`DH500ACDC-E`, `ID3000`→`NGU`), y un canónico con COMODINES
   (`W*A-*C-I02`) = issue de calidad del catálogo (de vuelta a E1).

## Propuesta de evidencia: ATESTACIÓN DE CONTENIDO (patrón DEC-193)

Para las clases 2 y 3, por pareja (doc a doc): ¿el término canónico aparece
en el CONTENIDO de los chunks del documento (imatch sobre content, no sobre
pm)? Tres salidas:

- **ATESTADA** (canónico presente en el texto del doc): la adjudicación de
  doc_map + la atestación del propio manual = evidencia doble → APLICAR.
- **NO ATESTADA**: el manual no menciona su supuesto producto canónico →
  PACKET a Alberto (con conteos y muestras de content).
- **AMBIGUA en estrechamientos** (el texto menciona el canónico Y otras
  variantes de la misma base: caso ONE 500 vs ONE-LOOP, ASD 533-1 vs 533-2):
  → PACKET SIEMPRE (el estrechamiento pierde findability de las hermanas —
  la clase DEC-192/193; ningún autómata decide esto).

Orden de ejecución propuesto: (1) clase 1 con el criterio REPARADO (normkey==
Y sin signos semánticos divergentes); (2) sonda de atestación (solo lectura,
~102 queries de content); (3) aplicar ATESTADAS no-ambiguas con el writer ya
validado (CAS + findability); (4) packet con el residuo; (5) sonda E2-POST
con diff pre-registrado.

## Gaps declarados

- La atestación por content puede dar falso-NO en manuales que nombran el
  producto solo en portada/tablas mal extraídas — por eso el NO va a packet,
  jamás a descarte.
- El writer no cambia: mismo backup por-chunk + CAS + gates (r24).
- Los 2 derivados + 166 no-consumibles siguen FUERA (packet E1/E1b).
