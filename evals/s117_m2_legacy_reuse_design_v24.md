# S117 M2 — aclaración v2.4: binding sidecar autoritativo

Este addendum corrige el bypass detectado adversarialmente en v2.3. Cambiar
`sidecar._ROOT` no controla un `source_path` absoluto: el módulo usaría la
carpeta absoluta original y podría consumir un sidecar distinto del sellado.

Antes de materializar cada raw, las rutas reconocidas como canal portal deben:

1. ser relativas;
2. tener exactamente dos componentes (`Manuales_<canal>/<archivo>`);
3. no contener `.` ni `..`;
4. conservar como primer componente el canal reconocido por
   `config/portal.yaml`.

El auditor normaliza separadores a `/` y usa esa ruta canónica tanto para
`sidecar.lookup()` como para B5. Cualquier ruta portal absoluta, anidada o que
escape el root falla antes de cargar `DATABASE_URL`. Los tests incluyen un
sidecar señuelo externo y demuestran que nunca puede ser consumido.

No cambia el contenido de los cuatro sidecars sellados, los 95 lookups
esperados, el SQL remoto, el matching ni la taxonomía.
