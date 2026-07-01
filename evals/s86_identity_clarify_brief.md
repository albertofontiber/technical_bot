# s86 · Propuesta BP — resolución de identidad + clarify-on-ambiguity (¿es BP o quick-fix?)

> Para el dúo adversarial (Protocolo 3). Pregunta central de Alberto: **¿es esto BP en RAGs
> de este estilo, o es tapar-agujeros?** NO queremos quick fixes. Zona de dolor: retrieval/identidad.

## Contexto medido (s86)
Bot RAG Telegram PCI (Claude genera + Supabase pgvector, chunks_v2 Voyage-1024). Corpus multi-fabricante,
escala objetivo 30+. El eval mide **hechos** en la respuesta (juez GPT-5.5). El bot ya tiene 3 modos:
`answer | ask_clarification | admit_no_info`.

Problema: **ambigüedad de entidad de producto**. "Morley RP1r" matchea 4 productos DISTINTOS (RP1r-Supra=Notifier,
VSN-RP1r=Morley-extinción, RP1r-a-secas, OPC-RP1r-software). `product_model` en la DB es doc-level y colisiona por
substring (afp400⊂afp4000; los 4 RP1r bajo el token "rp1r"). Historia medida esta sesión:
- Filtro substring curado (LEVER2_IDENTITY, YAML por-familia): resuelve el paraguas ZXe (+4 hp018) pero solo 3
  familias curadas; no escala.
- Filtro data-driven (mapa s83 family_scope): resuelve ZXe data-driven PERO **regresa hp011 (−2)** porque *adivina*
  RP1r→a-secas y **dropea el manual Supra correcto**. Net +1 < LEVER2 +3. Cada regla de matching nueva destapó otra
  fragilidad = **espiral de parches sobre ambigüedad real**.

## La tesis (a validar/refutar por el dúo)
Un *filtro* no puede resolver ambigüedad real: solo adivina (mal) o no filtra (contamina). La respuesta BP a la
ambigüedad de entidad **no es adivinar mejor — es CLARIFICAR**.

## Arquitectura propuesta
1. **Catálogo canónico curado** (familias/modelos/aliases/OEM-brand) sobre el activo s83 (2761 productos) + curación
   de las familias ambiguas. Curar = ground-truth de dominio mantenido (como el Excel de inventario), NO parche.
2. **Resolución query-side con detección de ambigüedad** usando TODAS las señales (modelo + brand "Morley" + función
   "extinción"), no solo el token. Vía **LLM query-understanding** contra el catálogo → {único | ambiguo | none}.
3. **Ramificar:** único → retrieval metadata-filtrado por el producto resuelto (filtro seguro, ya sin ambigüedad);
   ambiguo → **CLARIFY** (pregunta con los candidatos del catálogo); none → admite/amplio.
4. **Matiz** (clarify-vs-answer DEPENDE): clarificar **solo si la respuesta DIVERGE** entre candidatos. hp009 (EOL
   family-genérico, mismo valor) → answer; hp018 (variant-específico) → resolver; hp011 (extinción, diverge) → clarify.

## Reframe que expone
**hp011 NO es un retrieval-miss que parchear — es un caso de CLARIFY** mis-clasificado por el instrumento. La conducta
correcta ante "Morley RP1r" ambiguo es preguntar, no recuperar-y-adivinar.

## Alternativas descartadas
- Adivinar-el-más-probable (= lo que falla; brand no desambigua Supra/a-secas, ambos Notifier).
- Union-retrieve todos los candidatos (bloat zero-sum pool-50 + contaminación cross-product #11e/#11f).
- Solo-regex/heurística de contexto (frágil = la espiral actual).

## Gaps/riesgos declarados
- El eval puntúa HECHOS → un clarify correcto en hp011 puntúa "fallo" salvo que el eval **acredite el clarify**.
- LLM-query-understanding = +1 llamada (latencia/coste) — ¿justificado vs una tabla de desambiguación curada?
- hp011 gold-identidad (Morley-VSN vs Notifier-Supra) necesita adjudicación humana.
- Curación continua (acotada, O(familias-ambiguas)).

## Preguntas al dúo
1. ¿Es "catálogo curado + query-understanding + clarify-on-ambiguity" la **BP real** para RAG multi-producto con
   ambigüedad de entidad? ¿Qué hacen los sistemas de producción/la literatura?
2. ¿El **LLM query-understanding** es BP o sobre-ingeniería vs una tabla de desambiguación determinista?
3. ¿El matiz "clarify solo si diverge" es correcto o sobre-complejo? ¿Cómo se decide "diverge" sin recuperar antes?
4. ¿Queda alguna parte que siga siendo quick-fix / no-estructural?
5. ¿Cómo debe el eval (que mide hechos) acreditar un clarify correcto sin premiar el clarify-perezoso?
