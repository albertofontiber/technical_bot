# s88 — Paquete de adjudicación GOLD/JUEZ-review (Clase A del dossier) · para tu sí/no en lote

> ## ✅ RESUELTO (s89) — resultados del re-juicio dirigido (K=5) tras las marcas de Alberto
> | caso | marca | aplicado | resultado |
> |---|---|---|---|
> | A1 cat009 | ✅ | "suministrado"→condensador (literal ES) | sin movimiento (4-1 PARCIAL; el juez pide ahora la cita de revisión) |
> | A2 cat020 | ✅ | quitada "independiente del tipo de equipo" | sin movimiento (5 PARCIAL; el juez sigue penalizando OTM/LSR añadido = juez-bias → dual-judge) |
> | A3 cat024 | (b) | discrepancia 7-vs-17 como hecho + precedencia manual-del-dispositivo (verificada al píxel: MISMO modelo, 5 chunks) | **FALLO(2)+PARCIAL(3) → PARCIAL 5/5** (cola mejorada; el bot lideró con 7 mA sin precedencia → bot, no gold) |
> | A4 hp004 | (a) | nota de equivalencia answer-ambas+confirmación | **PARCIAL(4-1) → PASS 5/5 UNÁNIME** ✅ |
> | A5 cat012 | — | **RESUELTO SOLO**: ya es PASS 5/5 unánime en s87 (está en el PASS-control). La línea "residual PARCIAL" de abajo era dato STALE de s67base — error del autor del packet, corregido. | nada que adjudicar |
>
> **Neto:** PASS-map actual = **10/39** (+hp004); cat024 sin FALLOs. cat009/cat020 confirman el plateau
> (el juez completista encuentra el siguiente hecho) → refuerza dual-judge como el lever del bucket.
> Pregunta ES/EN de A1 → respondida (BP: no excluir; language-variants al catálogo F1). Nota respondida en sesión.

> **Cómo usarlo (~15-20 min):** cada caso trae el literal del manual + lo que dice el gold + la
> edición PROPUESTA. Marca ✅ (aplicar tal cual) / ✏️ (aplicar con tu matiz) / ❌ (el gold se queda).
> YO aplico después las ✅/✏️ vía `gold_store` (la puerta valida) y re-mido SOLO los golds tocados
> (K=5 dirigido, barato). **Nada se toca sin tu marca** (DEC-025: el gold es tuyo).
> Los casos de JUEZ (no de gold) van aparte al final — no son editables, son evidencia para el dual-judge.

---

## A1 · cat009 — la 6K8 como "suministrada" ‖ K-INESTABLE (2 PASS / 3 PARCIAL) — el más cercano

**Pregunta:** ¿Qué resistencia de fin de línea (EOL) hay que instalar en las líneas de zona de la central NFS Supra?
**Literal del manual SERVIDO** (HLSI-MN-025, ES p27, chunk F5): «Las líneas de zona deben terminarse en
el último equipo, con un equipo final de línea **(EFL) de condensador de 47µF (suministrado)** o
resistencia **(RFL) de 6K8Ω**…» — el "(suministrado)" acompaña SOLO al condensador.
**El gold dice:** «…la resistencia de fin de línea (EOL) **suministrada** de 6K8 Ω (6,8 kΩ), o bien con
el condensador de 47 µF **que viene por defecto**…» — atribuye "suministrada" a la 6K8.
**Nota:** el gold cita la edición EN (HLSI-MN-025-I v05 p27: "supplied 47µF capacitor or 6K8 Ω resistor"
— parse AMBIGUO en inglés; el ES lo desambigua hacia el condensador). El sub-agente verificó ambas ediciones.
**El bot dijo** (fiel al ES): condensador 47µF suministrado/por defecto + resistencia 6K8 como alternativa,
"no se especifica como suministrada".
**EDICIÓN PROPUESTA:** en el gold, mover "suministrada" → el condensador («el condensador de 47 µF
suministrado (por defecto), o bien la resistencia de 6K8 Ω») y quitar la exigencia implícita de que el
bot afirme la 6K8 como suministrada.
**Impacto esperado:** K-INESTABLE al borde → candidato a re-juicio (no promesa; PASS es holístico ±2).

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: _En estos casos en los que EN =ES, ¿deberíamos excluir el manual en inglés para reducir el ruido? ¿cómo se gestiona en RAGs BP con esta problemática?

---

## A2 · cat020 — "0-100% independiente del tipo de equipo" ‖ residual (5 PARCIAL)

**Pregunta:** nivel de alarma y prealarma por defecto en la Morley DXc (España).
**Lo verificado:** el chunk servido F2 contiene TANTO el literal del gold («valor analógico… normalizado
entre 0% – 100%… prealarma 80%… alarma 100%… máximo 108%») COMO las pantallas de config por Niveles
(«Introd nivel Fuego: 3», OTM/LSR). **El bot acertó los 3 números core** (80/100/108, citando F2) y
AÑADIÓ la desagregación OTM/LSR-por-niveles — correcta según el manual. El juez la lee como contradicción
del «independiente del tipo de equipo» del gold.
**EDICIÓN PROPUESTA:** matizar el gold: «…es un número normalizado 0-100% (la ESCALA analógica es común;
en la config de campo algunos tipos (OTM/LSR) se ajustan por Niveles 0-9 que mapean a esa escala)» — o
al menos quitar «independiente del tipo de equipo» como hecho exigido.
**Impacto esperado:** residual 5-PARCIAL → el hecho-conflicto desaparece; sin promesa de flip.

**TU MARCA: [X] ✅ [ ] ✏️ [ ] ❌** — notas: ______________________

---

## A3 · cat024 — conducta ante la discrepancia MAD-472 vs tablas CAD-250 ‖ residual (3 PARCIAL / 2 FALLO)

**Situación:** el bot acertó el dato del manual objetivo (17 mA a 80 dB(A) del MAD-472) e introdujo la
discrepancia de las tablas del CAD-250 (7 mA) RECOMENDANDO VERIFICAR. El juez lo castiga por no resolver.
**Contexto de diseño:** `conducta_esperada=answer`; la política del proyecto para conflictos documentales
es «surfacear ambos, NO resolver» (briefing/adversarial + answer-con-conflicto existe como conducta).
**PROPUESTA (elige una):**
 (a) cambiar `conducta_esperada` → `answer-con-conflicto` (el bot YA la ejerce);
 (b) añadir al gold la discrepancia como hecho esperado («las tablas del sistema CAD-250 listan 7 mA;
     ante discrepancia, prevalece el manual del dispositivo / verificar en campo»);
 (c) ❌ dejarlo (si tu ground-truth es que 17 mA es EL dato y mencionar 7 mA confunde).
**TU MARCA: [ ] a [ ] b [ ] c** — notas: ¿estamos 100% seguros de que hay un conflicto, o es que por ejemplo el valor depende del modelo de la familia?

---

## A4 · hp004 — clarify vs answer-ambas-versiones ‖ K-INESTABLE (1 PASS / 4 PARCIAL)

**Situación:** gold=`clarify` (DGD-600 tiene versión 24V y 220V con specs DISTINTAS → diverge). El bot
dio AMBAS versiones con specs correctas + pidió verificar la instalada. Funcionalmente cubre el criterio
s79/s80 (la divergencia está surfaceada); formalmente no es un clarify puro.
**PROPUESTA (elige una):**
 (a) aceptar answer-ambas-ramas+advertencia como cumplimiento de clarify cuando el bot CUBRE todas las
     variantes (editar `conducta_esperada` → clarify|answer-ambas o anotar equivalencia en el gold);
 (b) ❌ mantener clarify estricto (el técnico DEBE identificar su versión antes de recibir specs — más
     seguro en campo si mezclar specs es peligroso).
**TU MARCA: [X] a [ ] b** — notas: ______________________ *(b es defendible en PCI; tu llamada de dominio)*

---

## A5 · cat012 — "gold-injusto debatible" desde s71 ‖ residual (PARCIAL; era PASS-modal en s67base)

**Situación:** ya auditado en s71 (único superviviente "maybe-injusto" del audit) y s74. Flickerea con el
juez. Sin edición concreta propuesta — **pregunta directa:** ¿quieres que prepare el desglose per-hecho de
cat012 (como A1/A2) para la próxima tanda, o lo cerramos como "ruido de juez, esperar dual-judge"?
**TU MARCA: [ ] preparar desglose [ ] cerrar como ruido** — notas:¿qué me recomiendas? ¿tiene sentido revisar el gold para que deje de ser "maybe-injusto"?

---

## NO editables (evidencia para el dual-judge / rubric — gated ~sept, DEC-051d/075f)

- **cat019** — falso NO-PASS del juez TRIPLE-confirmado (s76: audit humano should_be=PASS; sesgo
  completitud-correcta≠contradicción). Nada que editar en el gold; es EL caso ancla del dual-judge.
- **hp013/hp020/cat010/cat009** — K-INESTABLES con votos PASS: se estabilizarían (o no) con dual-judge;
  hipótesis, no resultado.

## Qué pasa tras tus marcas
1. Aplico las ✅/✏️ vía `gold_store` (validación de la puerta; provenance = tu adjudicación s88).
2. Re-mido SOLO los golds tocados (bvg dirigido K=5, ~$2-3) — sin re-correr el eval entero.
3. Registro el delta honesto en DECISIONS (sin prometer flips: PASS es holístico ±2).
