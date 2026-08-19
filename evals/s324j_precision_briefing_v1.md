# s324j — Sello FINAL del cross-model sobre el HEAD terminal del cableado (Protocolo 3)

**Qué se revisa**: el commit `4bc77cd`, que aplica los seis cierres de PRECISIÓN
de la ronda anterior (diff en `evals/s324j_precision_fixes.diff`; código en
HEAD). Todos fueron de exactitud de claims / honestidad de tests / prosa —
ninguno de mecanismo. Esta ronda es el sello final: ¿los cierres dicen la
verdad, o introdujeron una nueva sobre-afirmación? (mis dos tandas anteriores
de fixes tuvieron imprecisiones que este revisor cazó — de ahí el sello.)

**Los seis a verificar**:
1. Runbook: «encender ip: cierra el bypass de UNA IP; un botnet con IPs
   rotatorias es el límite estructural declarado». ¿Exacto ahora?
2. `auth.py` docstring de `admitir`: la paridad con el SQL es de BLOQUEO/BACKOFF;
   la RETENCIÓN diverge (RGPD). ¿Bien acotado?
3. Autocontrol de la ventana (019): declarado BEST-EFFORT anti-sabotaje, no
   verificación semántica exacta. ¿Honesto?
4. `cerrojo.py` docstring + addendum de la v9: registran el orden nuevo
   (check→poda→cap→conteo) como supersesión de §3.2. ¿Coherente con el SQL?
5/6. Tests pg renombrados (`ultimo` no prueba monotonía fuerte; `acierto` es
   secuencial): ¿los nombres/docstrings ahora coinciden con lo que prueban?

**Contexto que NO se re-litiga**: el diseño v9, el cableado (veredicto FIEL) y
el reorden de `panel_puerta` (ya validado en la ronda de verificación, gate pg
17/17). Solo se revisa que los cierres de precisión sean exactos.

**Nota de instrumento**: el 2º revisor frontera Anthropic (Fable/Opus) está
caído por CRÉDITO AGOTADO (400 «credit balance too low», verificado con sonda
mínima; DEC-236). Esta ronda corre solo el cross-model Sol — el lado
innegociable del Protocolo 3.

**Verificación del autor**: suite 4517 passed / 62 skipped / 2 xfailed; gate pg
REAL 17/17 + ACL 12/12.
