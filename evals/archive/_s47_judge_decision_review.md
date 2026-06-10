# Medir-primero §D (DEC-021): ¿DIFERIR el dual-judge? — REFUTA mi interpretación

## Contexto
Para decidir si construir un dual-judge (Claude+GPT votando los ejes de seguridad), medí el
DESACUERDO entre **GPT-5.5 (juez canónico ACTUAL)** y **Claude-Opus (candidato)** sobre el eje
FACTUAL del scorer, sobre las 22 respuestas del bot (`bot_vs_gold_results_k5.yaml`).
- Ronda 1 (booleano "¿hay contradicción?"): **8/22 = 36% desacuerdo**.
- Ronda 2: inspeccioné el CONTENIDO de los 8.

## El eje (diseño del scorer — verifícalo en `atomic_scorer.py`)
El eje FACTUAL es **CONTRADICCIÓN-ONLY** (DEC-012): solo marca si el bot AFIRMA algo que choca
con un valor documentado. La INCOMPLETITUD (el bot no da un dato) la mide COMPLETITUD, no este
eje. Que el bot diga "no tengo X / los fragmentos no contienen X" es conducta SEGURA (honestidad),
NO contradicción — esa es la jerarquía Seguridad>Honestidad>Utilidad de `RULER_DESIGN §1`.

## Los 8 casos (contenido real capturado de cada juez)
- **cat005, hp015**: en la ronda 2 AMBOS dicen "sin contradicción" (el True de ronda 1 no se reprodujo).
- **cat007**: GPT none. CLAUDE marca: hecho="el relé de AVERÍA es failsafe"; bot dice="los fragmentos no describen explícitamente el comportamiento del relé ante corte"; por_qué="el bot afirma que el manual no especifica el fail-safe, cuando el hecho está verificado".
- **hp006**: GPT none. CLAUDE marca: hecho="la MPS-400 tiene detección de fallo de tierra (LED dedicado)"; bot dice="los fragmentos (MFDT170/MIDT170) no contienen información"; por_qué="el bot dice que MIDT170 no tiene info de fallo de tierra, pero los hechos verificados dicen que sí".
- **hp008**: GPT none. CLAUDE marca: hecho="la comunicación del lazo usa protocolo CLIP"; bot dice="todos usan protocolo de comunicaciones Notifier"; por_qué="el bot no especifica que es CLIP".
- **hp010**: GPT none. CLAUDE marca: hecho="procedimiento: Nivel 3 + desbloquear memoria + menú…"; bot dice="el procedimiento paso a paso no está en los fragmentos recuperados"; por_qué="el bot dice que no lo tiene, pero los hechos verificados confirman que existe".
- **hp003**: CLAUDE none. GPT marca: hecho="orden seguro: PRIMERO red (230VAC), DESPUÉS baterías"; bot dice="conecta el cable puente entre baterías antes de cualquier otra conexión"; por_qué="el bot pone las baterías antes, choca con el orden de seguridad verificado".
- **hp001**: GPT none. CLAUDE marca: hecho="del MENÚ PRINCIPAL: Lazos, Sectorización, Maniobras, Logs, Red, Ajustes, Instalación"; bot dice="…Lazo, Sectorización… (y añade 'Mapas')"; por_qué="el bot añade 'Mapas' (no documentado) y dice 'Lazo' singular".

## Mi adjudicación
- 2 = **ruido de sampling** (cat005, hp015).
- 4 = **Claude SOBRE-marca** incompletitud honesta como contradicción (cat007, hp006, hp008, hp010); GPT canónico NO = correcto.
- 1 = **GPT caza un FALLO real de seguridad** (hp003, orden de baterías); Claude lo pierde.
- 1 = Claude caza borderline (hp001, 'Mapas'/singular) que GPT pierde.

## Mi conclusión — LA QUE DEBES REFUTAR
**DIFERIR el dual-judge.** El juez canónico GPT-5.5 está bien calibrado (no infla incompletitud);
el desacuerdo lo causa el CANDIDATO (Claude) sobre-marcando. Añadir Claude = +4 falsos-flags por
~1 catch = mal trade. El A/B de contextual-retrieval va con GPT-5.5 único congelado.

## Riesgos que YO veo en mi propia conclusión (atácalos Y busca más)
1. **CONFIRMATION BIAS**: yo ya tenía lean "diferir". Ronda 1 lo contradijo (parecía "construir"). Ronda 2 me devuelve a "diferir". ¿Interpreté la ronda 2 para regresar a mi prior?
2. **SINGLE-RUN**: la inspección es n=1 por modelo — el mismo ruido que critico. ¿"Claude sobre-marca" es ESTABLE o sampling? (2 de los 8 ya resultaron ruido).
3. **¿Es correcto mi "incompletitud honesta ≠ contradicción"** contra los golds/respuestas reales, o descarto catches VÁLIDOS de Claude para salvar la conclusión? (cat007/hp006/hp010: el bot dice "no lo tengo" PERO el dato existe en el corpus → ¿no es eso un fallo material aunque el bot sea "honesto"?)
4. **¿Infravaloro el dual-judge?** hp003 y hp001 muestran que CADA modelo caza cosas que el otro pierde, EN AMBAS direcciones — ¿no es eso exactamente el argumento PRO-ensemble que estoy descartando?
5. **hp003**: ¿es FALLO real (un técnico conectaría baterías en orden inseguro) o ruido de un solo run de GPT? Verifícalo contra el gold/fuente si puedes.
