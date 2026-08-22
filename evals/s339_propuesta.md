# s339 — Lote de catálogo desde el packet firmado por Alberto

## Qué es esto

Alberto ha revisado y anotado uno a uno `docs/REVISION_ALBERTO_HUERFANOS.md`: 24 decisiones
(23 casillas marcadas) y 46 anotaciones de dominio. Este lote traduce esas adjudicaciones a
mutaciones de catálogo. **59 operaciones**, simuladas sobre copia: **82 → 35 huérfanos**
(cierra 47, abre 0), `catalog_store.validate` limpio.

Cadena de ficheros nuevos (ninguno toca `data/catalog/` ni `src/`):
- `scripts/s339_ledger_alberto.py` → `evals/s339_ledger_alberto.json` (extracción)
- `scripts/s339b_verifica_ledger.py` → `evals/s339b_verificacion.json` (verificación contra catálogo vivo)
- `scripts/s339c_plan_lote.py` → `evals/s339c_plan_lote.json` (mutaciones + simulación)
- `tests/test_s339_ledger_cita_a_alberto.py` (5 tests)

## El diseño que quiero que ataques

**Separación mecánico / interpretado.** El packet es prosa. `s339` separa lo que Alberto
escribió (parseado del fichero, sin interpretar) de **mi lectura** de esa prosa en acciones de
catálogo (mapa `LECTURA`, escrito a mano). Cada lectura lleva un campo `cita` con el fragmento
del que sale, y un test verifica que **toda cita está literalmente en el packet** (permitiendo
elidir con «…» pero no reescribir — ni siquiera para corregirle una errata).

**Por qué no auto-interpreto la prosa con un LLM:** porque entonces «lo que Alberto dijo» y «lo
que yo entendí» serían la misma celda, sin traza. Ataca esto si crees que es al revés.

## Lo que la verificación ya cazó de mi propia lectura (y corregí)

1. `§4.4 APIC` — yo proponía FUSIONAR aritech:apic + notifier:apic. Ya existe un homónimo
   `APIC` con `politica: clarify`, **adjudicado por Alberto en s91**, con los dos productos
   candidate A PROPÓSITO (tarjetas incompatibles). Propuse contra su propia decisión vigente
   por no grepear `homonyms.jsonl` antes. Ahora: cero cambios; su manual es suelo permanente.
2. `§2.2/§2.4/§4.1/§4.2/§4.3` — el id GANADOR de la fusión está él mismo en cuarentena.
   Redirigir hacia un `candidate` no rescata nada (`_consumable` sigue el redirect). La acción
   es de TRES pasos: promover ganador + redirigir perdedor + `vendido_bajo`.
3. `§2.2 TG-1020` — promoverlo choca con `desico:tg-1020` consumible (canonical duplicado).
   Es la pregunta que le hice al final del packet y **sigue sin responder** → EXCLUIDA del lote.
4. `§6.4 RHistorico` — yo creaba `notifier:rhistorico`. Ya existe `notifier:rhistorico.exe`
   con «Utilidad de Reparación de Históricos» **ya como alias**. Ahora: renombrar el
   `canonical_model` del id existente (el id es inmutable, el canónico no) y bajar el .exe a alias.
5. `suelo F5000` — Alberto dice «el modelo F5000 de Morley». El catálogo ya tiene `ffe:f5000`
   consumible, **adjudicado por él en s91**. FFE fabrica y Morley revende → `vendido_bajo` con
   las dos marcas en el id existente, en vez de crear `morley:f5000` (canónico duplicado).
   **Divergencia declarada: hay que confirmársela.**
6. `§7 unresolved:trd-100` — promoverlo Y crear `detnov:trd-100` duplicaba el canónico. Ahora
   redirect al id con marca; el manual atesta DOS productos (TRD-100 y TSD-100).
7. `§5.1 colapso de id` — Alberto pide ELIMINAR `notifier:notifier-inspire-e10` en vez de
   redirigirlo. Verificado: nació y sigue `candidate`, así que nada externo lo referenció y
   borrarlo no rompe el contrato de inmutabilidad (que protege ids publicados). Los alias que
   lo referenciaban se repuntan al destino.

## Lo que sigue BLOQUEADO y por qué

- `§2.2 TG-1020` — pregunta sin responder (arriba).
- `suelo MADT190_10` — 9 racks Notifier cuyos canónicos son **sólo dígitos** (`020-596`…), y el
  detector los excluye a propósito. Crearlos no los hace alcanzables.
- `suelo D 1100-4` — `CWSO-xx-{S1,S2,W1,W2}` donde «xx» es el color: patrón, no modelo instanciable.
- `suelo FS2-1` — dice «la familia FS … de 1, 2 y 4 zonas»: ¿id de familia o tres modelos?
- `suelo MNDT021` — única fila que no anotó.

## Preguntas que te hago explícitamente

1. ¿La separación mecánico/interpretado es real, o el mapa `LECTURA` es interpretación
   disfrazada de datos? ¿Qué lectura concreta NO se sigue de la cita que dice citar?
2. Las 12 promociones: ¿alguna re-abre el mecanismo hp009/DEC-091b (R20 — promover quita el
   paraguas `models` bajo `replace`)? La simulación dice «abre 0» contando huérfanos.
   **¿Es «huérfanos» la métrica correcta para detectar esa pérdida, o mide otra cosa?**
3. `_marca()` mapea namespace → grafía canónica (`morley` → `Morley-IAS`). ¿Qué se rompe si
   la grafía mayoritaria del catálogo no es la que usa el filtro de marca en runtime?
4. El colapso de `§5.1`: ¿me estoy saltando la inmutabilidad con una excusa?
5. ¿Qué NO he mirado que debería, antes de meter esto por la puerta `s324`?
