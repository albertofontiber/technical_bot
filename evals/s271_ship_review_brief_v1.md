# S271 — Review de SHIP del Bloque A (dúo: lado Sol; Fable ya emitió SÓLIDA en build)

Objeto: merge de `claude/s271-activation-fixes` (stacked sobre s270): guards v4 + whitelist
fail-closed v5 en `src/rag/must_preserve.py` (DEC-129/130), re-spec opción-1 del disclosure
(DEC-128, adjudicado por Alberto), adjudicación CLIP-CORE registrada.

Evidencia: validación fresca seed-275 GO y seed-276 GO (clases nuevas 0 FP; coste whitelist
VISIBLE: 15.3% skips por-diseño) · cert det-only v2: b6f6 3/3 + 872c 2/3 (ESTABLE ≥2/3, matiz
r3 declarado sin tunear) · Etapa 3 v3 ruta viva: monotonía 5/5, 0 apéndices espurios ·
Fable-review del build: SÓLIDA con 2 medios cableados y re-medidos.

Preguntas (bite con ancla): (1) ¿defectos de código en la whitelist `atom_good_form` / guards
v4 que hagan inseguro el ON en demo? (2) ¿la cadena seed-275/276 + cert v2 + smoke v3 tiene
huecos que invaliden "2 conversiones estables + 0 ruido"? (3) ¿el matiz 872c 3/3→2/3 está
honestamente tratado o esconde fragilidad material? (4) ¿algo del stacking s270→s271 rompe
al merge? NO es objeto re-litigar DEC-125/126/128 (adjudicados por Alberto).
