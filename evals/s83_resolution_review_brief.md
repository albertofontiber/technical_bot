# Revisión adversarial — FIDELIDAD del encoding de los 29 conflicts adjudicados (s83, zona de dolor identidad)

## Qué se revisa
Alberto (ground-truth de dominio PCI) adjudicó a mano los 29 conflicts de cobertura. Yo (Claude) traduje su
prosa a registros estructurados en la tabla `document_models`. **La pregunta NO es si la adjudicación de Alberto
es correcta** (él es la verdad) — es **si YO la encodé con fidelidad**: ¿perdí algo que dijo cubrir, cubrí algo
que dijo descartar, asigné mal un bucket, o introduje un error en el fold-in?

## Insumos (3 capas)
1. `evals/s83_conflicts_groundtruth.yaml` — la **prosa** de Alberto (campo `decision:` por doc). LA VERDAD.
2. `evals/s83_conflicts_resolved.yaml` — **mi traducción** a buckets: `primary/secondary/candidate/software/compat/mention/drop` + `aliases`.
3. `evals/s83_29_final_dump.md` — el **registro final** resultante (canonical + aliases + compatible_with + mentions + flags).
   Lógica del fold-in: `scripts/s83_finalize_tables.py` (enriquece cada nombre desde la extracción cruda por match de keyset normalizado).

## Buckets / reglas que apliqué (para que las juzguéis)
- **covers vs mentions** (principio rector de Alberto): cubre = el doc da contenido accionable SOBRE el producto;
  menciona = compatibilidad/objetivo/accesorio nombrado/part-number → NO covered (va a `compatible_with` o `mentions`).
- **software** → `category=software` + los paneles objetivo → `compatible_with` (aplicabilidad, NO covered).
- **drop** → NO-producto excluido entero (config .exe `OPC-RP1rcfg`, SKU de soporte `787640`, `TBUD-250` solo-mención, `Wavecom GSM`).
- **candidate** → cubierto con info limitada / tiene manual propio (role=secondary, candidate=true).
- **central multi-producto** → primary = la central/sistema; módulos = secondary.

## Lo que pido (bite concreto, por doc cuando aplique)
1. **Fidelidad**: recorre los 29. ¿Algún caso donde mi `resolved`/registro-final **NO refleja** lo que Alberto escribió?
   (p.ej. un módulo que él dijo "cubierto" y yo dejé fuera; un "solo mencionado" que yo metí como covered; un drop que no se aplicó).
2. **Buckets dudosos**: ¿algún `compatible_with` que debería ser `covered` o viceversa? ¿algún `software` mal puesto?
   ¿`candidate` vs `secondary` bien? Casos a mirar: TG-NOTIFIER/UPDL/PK-* (software+compat), Pearl (primary+módulos),
   XP transponder (MNDT350, ~20 módulos), CAD-250 (variantes+software SCD250), SMART 3G (accesorios candidate).
3. **El FS** (`FS2-1` → encodé `FS-1/FS-2/FS-4`, flag `confirm:true`): ¿encoding razonable o arriesgado? Alberto dudaba de la designación exacta.
4. **Pérdida de info en el fold-in**: ¿el enriquecimiento por keyset puede pegar un alias EQUIVOCADO a un nombre? ¿el filtro `drop` puede borrar de más?
5. **Schema a 30+**: ¿`software`/`compatible_with`/`recall_incomplete` son las estructuras correctas, o falta algo (p.ej. relación tipada por-módulo)?

Distinguid BUG (encoding objetivamente infiel a la prosa de Alberto) de DECISIÓN (mi criterio defendible). Verificad contra los 3 ficheros antes de afirmar.
