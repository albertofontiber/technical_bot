# Propuesta s47 — Criterios de éxito explícitos (el "gate" auto-ejecutable)

## Qué se decide y por qué
Formalizar los criterios de éxito del Technical Bot PCI en un gate que se auto-ejecute,
para que el humano (Alberto) deje de adjudicar "¿esto es suficiente?" caso a caso y su
supervisión se concentre en lo irremplazable. NO es construir aparato nuevo: es consolidar
en un sitio cosas ya decididas por medición en sesiones previas. Impacto: MEDIO en zona de
dolor (toca el esquema/uso del ruler) → revisión dual (sub-agente + cross-model).

## Restricciones que los criterios DEBEN respetar (decidido por MEDICIÓN, no opinión)
Un criterio que contradiga esto es un error — cázalo:
- **Ruler diagnóstico, NO gate estadístico** (DEC-003, RULER_DESIGN §0). La parada del eval
  set es cobertura de TAXONOMÍA, no un N.
- **"Recall no convierte"** (DEC-005, s44): mejorar recall históricamente NO movió veredictos
  end-to-end. El árbitro es end-to-end, no el funnel/proxy.
- **Síntesis-genuina ≈ 0** (gate s46): con el chunk en top-5 el bot lo usa; la síntesis NO es
  el cuello. (La "síntesis domina" previa era artefacto de un matcher sin frontera-dígito.)
- **retrieve-wide** (top_k 15→50, s44/DEC-018) cerró los FALLO peligrosos (FALLO ~6→1).
- **Juez ruidoso**: el eje factual es no-determinista (TECH_DEBT #37) → K-mayoría + flag, no
  single-pass. Hay un suelo de ruido que ningún delta debe confundir con señal.
- **Prosa-frágil**: la completitud mecánica se infra-cuenta (#35) → PARCIAL es un SUELO de
  medición, no necesariamente un fallo real de calidad.
- **Eje no-fabricación / asimetría de seguridad** (DEC-012): afirmar un hecho "ausente-probado"
  (que el corpus no soporta) = FALLO, aunque no contradiga nada.
- **Contexto de negocio**: Fontiber M&A en due-diligence; SIN técnicos reales hasta meses → no
  hay usuarios todavía. Sobre-medir calidad ahora puede ser rigor mal dirigido (lección s27).

## Los criterios propuestos

### §A — Definition-of-Done de Fase 1 «calidad» (cuándo es "suficiente pre-técnico")
F1 se declara suficiente cuando, sobre el ruler:
1. **0 FALLO-peligroso**: cero invención-sobre-vacío (eje no-fabricación) Y cero dato-crítico
   mal citado (eje factual). El bot puede ser INCOMPLETO; no puede mentir con confianza.
2. **Residual PARCIAL 100% explicable**: cada PARCIAL es suelo-de-medición (#35) / secundario
   de pregunta multi-parte / recall-miss-de-corpus documentado — NO un mecanismo de calidad
   sin atacar.
3. Cada FALLO no-peligroso restante con **causa clasificada + decisión** (atacar / diferir-con-razón).

NO hay umbral de "%PASS". Justificación: ruler diagnóstico no estadístico (DEC-003); sin
usuarios un % es rigor mal dirigido (s27); PASS se deflacta por prosa-frágil (#35) → un %
mediría el ruido del juez, no calidad real.

*Alternativa descartada:* piso de %PASS (p.ej. ≥80% antes de expandir fabricantes). Descartada
por las tres razones de arriba. (Este es el punto donde el autor MÁS quiere challenge: ¿el
"no %PASS" es correcto, o es una excusa cómoda para no ponerse un listón medible?)

### §B — Ship-criterion de un lever (de "probado" a "desplegado")
Un lever se shipea SÓLO si, en A/B sobre el ruler:
1. Mueve **VEREDICTOS** (PASS/PARCIAL/FALLO), no proxies de recall.
2. **Dos ejes**: completitud↑ SIN invención↑ (DEC-001). Sube-completitud-pero-mete-alucinación = rechazo.
3. **Delta > ruido del juez**: K-mayoría, no single-pass (#37).
4. **No-regresión** de lo que ya funciona: diagramas/wiring (boosts load-bearing) + los PASS actuales.
5. **Coste/latencia declarados** (p.ej. rerank ~3-7× latencia) — aceptable o trade-off documentado.
Si no cumple → NO se shipea; se documenta el delta y el porqué.

### §C — Crecer el eval set (Track B en paralelo, gestión del riesgo de atribución)
1. Crece por **breadth de taxonomía** (fabricante/conducta/idioma/modalidad nuevos), NO por más
   `answer` del mismo tipo. Parada = cobertura, no un N (DEC-003).
2. **Slice separado, tag `s47-breadth`**: el A/B de contextual-retrieval se mide sobre el ruler
   ACTUAL (22 golds, CONGELADO como baseline). Los golds nuevos NO entran en el delta de ese
   experimento hasta una corrida posterior. Así se crece en paralelo sin contaminar la atribución.
3. Cada gold nuevo pasa por el proceso C4 source-anchored (locate_fact + co-gen GPT-5.5 +
   doble-lectura + dúo C3 + regla C + gold_store.upsert). NO se relaja.

## Encargo al revisor (REFUTA, no confirmes)
1. ¿§A esconde un riesgo? ¿"0 FALLO-peligroso + residual explicable, sin %PASS" deja pasar un
   bot malo, o es el bar correcto dado que no hay usuarios? ¿El "no %PASS" es rigor honesto o
   racionalización?
2. ¿El ship-criterion §B tiene un agujero — algo que dejaría shipear un lever que no debería, o
   bloquearía uno bueno?
3. ¿El slice-tag de §C REALMENTE evita la contaminación de la atribución, o hay una vía por la
   que los golds nuevos sí ensucian el delta del A/B?
4. ¿Algún over-claim de FRAMING del autor (su sesgo conocido)? ¿Esto es estructural y escalable a
   30+ fabricantes, o es ritual disfrazado de gate?
