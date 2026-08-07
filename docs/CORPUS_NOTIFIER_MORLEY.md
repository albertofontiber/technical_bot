# Runbook — corpus de Notifier España y Morley-IAS España (portales HLSI)

> **Qué es.** Método reproducible para descubrir y descargar manuales de `notifier.es` y
> `morley-ias.es` (ambos de Honeywell Life Safety Iberia). Hermano del runbook
> `docs/CORPUS_FIRESECURITYPRODUCTS.md`, que cubre otro grupo (Carrier/Kidde: Aritech,
> Edwards, Kilsen, Ziton) y **NO sirve para estas marcas** — son fabricantes distintos.
>
> **Estado**: método verificado el 7-ago-2026 (s303) con descargas reales. Cosecha
> completa guardada en `data/catalog_portales/s303_portales_notifier_morley_v1.json`
> (844 entradas, 813 títulos únicos).

## 1. El hallazgo: el índice NO está cerrado

La creencia previa (packet s302) era que «los PDF están abiertos y el ÍNDICE está cerrado
tras el login», y que hacía falta un alta de partner para saber qué existe. **Es falso.**
El componente Joomla ZOO de ambos portales es completamente público:

```
https://www.notifier.es/index.php/component/zoo/alphaindex/{categoria}/{letra}/{pagina}
https://www.morley-ias.es/index.php/component/zoo/alphaindex/{categoria}/{letra}/{pagina}
```

- `{categoria}`: `manuales` (vigentes) · `manuales-des` (**des**catalogados — se corresponde
  con la carpeta `/manualesobs/` del servidor de ficheros).
- `{letra}`: `a`..`z`. `{pagina}`: **empieza en 1** y **pagina de 15 en 15**.
  ⚠️ **La trampa**: un scraper que no pagine se lleva solo los 15 primeros de cada letra y
  cree que ha cosechado todo. Silencioso.

Cada entrada del índice trae **título, idioma, familia y un enlace de descarga funcional**:

```
…/index.php/component/zoo/?task=callelement&format=raw&item_id=<N>
   &element=<uuid>&method=download&args[0]=<hash>
```

Ese enlace **sirve el PDF y devuelve el nombre de fichero real en `Content-Disposition`** —
que es como se resuelve *título → nombre de fichero* sin adivinar. Es superior a construir
URLs a mano (la regla «código sin guiones + `.pdf`» falla a menudo: hay ficheros con
guiones, con sufijo de revisión `rvNN`, y algunos con nombre totalmente distinto).

**Consecuencia**: para estas dos marcas **no hace falta darse de alta** para conocer el
catálogo. (El foro `morleyprofessional.co.uk` es otra cosa: ahí el legacy `996-xxx` sí exige
registro para descargar, aunque su índice se navegue sin él.)

## 2. ⚠️ WAF de Akamai — la trampa que invalida mediciones

Delante de `notifier.es` (y `notifier.be`) hay un **WAF de Akamai**. Una tanda paralela de
~1.100 peticiones HEAD provocó **bloqueo de la IP durante ~25 minutos**, y —esto es lo
importante— **el bloqueo responde 403, no 404**:

> Un probe rápido reporta «este fichero no existe» para ficheros que SÍ existen. La primera
> pasada de la cosecha de s303 quedó invalidada exactamente así y hubo que repetirla.

**Reglas obligatorias para cualquier barrido futuro:**
1. **Secuencial**, con ~3 s entre peticiones. Nada de paralelismo.
2. **Distinguir 403 de 404** en el código: un 403 NO es evidencia de ausencia — es evidencia
   de que hay que parar. Ante 403 repetido: abortar y esperar, no seguir barriendo.
3. Validar cada descarga (`%PDF` en cabecera + tamaño > 1 KB) y guardar procedencia.

## 3. Carpetas de ficheros (acceso directo, sin login)

| Marca | Carpeta | Contenido |
|---|---|---|
| Notifier | `/documentacion/notifier/manuales/` | Manuales vigentes |
| Notifier | `/documentacion/notifier/manualesobs/` | Manuales obsoletos (legacy) |
| Notifier | `/documentacion/notifier/hojastec/` | Hojas de características |
| Morley | `/documentacion/morley/manuales/` | Manuales vigentes |
| Morley | `/documentacion/morley/manualesdes/` | Descatalogados |

El listado de directorio devuelve **403** y no hay `sitemap.xml`: por eso el índice ZOO del
punto 1 es el camino, no la fuerza bruta.

## 4. Fuente alternativa útil (distribuidor)

Cuando un documento no está en los portales españoles —típicamente porque **solo existe en
inglés**— un distribuidor holandés publica material de Notifier con estructura navegable:
`support.topsecurity.nl/downloads/Brand/Notifier/…`. De ahí salieron en s303 los dos
documentos que el portal español no tiene (`997-412` y `997-415`). Verificar identidad
siempre: el nombre de fichero del distribuidor no sigue la convención de HLSI.

## 5. Estado de la cosecha (7-ago-2026)

| | Notifier | Morley | Total |
|---|---|---|---|
| Manuales vigentes | 375 | 122 | 497 |
| Descatalogados | 289 | 58 | 347 |
| **Entradas** | 664 | 180 | **844** (813 títulos únicos) |

Idioma declarado: 530 español · 92 inglés · 222 sin declarar.
Corpus actual de estas dos marcas: **705 documentos** (466 Notifier + 239 Morley).

**El cruce catálogo↔corpus está PENDIENTE** y es el trabajo que de verdad paga: exige
resolver los 844 enlaces a nombre de fichero (petición secuencial, ~45 min con la cadencia
segura del punto 2). Daría la lista de adquisición DEFINITIVA de los dos fabricantes
principales — muy superior al barrido por citas, que dio 84% de ruido (DEC-184/TECH_DEBT #62).

## 6. Límites declarados

- **Licencia**: que un PDF sea accesible no equivale a licencia de redistribución. Para uso
  interno del bot es un tema; publicar el corpus sería otro. Los términos de estos portales
  **no se han revisado**.
- **Fragilidad**: no sabemos si el acceso público al índice es intencional. Puede cerrarse.
  La cosecha guardada en `data/catalog_portales/` es, por eso, un activo con fecha.
- **Cortesía**: la cadencia del punto 2 no es solo para evitar el bloqueo — es lo correcto
  con un servidor ajeno.
