# -*- coding: utf-8 -*-
"""La fuente de marca de la PUERTA: Playfair Display, incrustada.

POR QUÉ INCRUSTADA Y NO DESDE GOOGLE. El Data Room usa `next/font/google`, que
**descarga la fuente en el build y la sirve desde su propio origen** — su CSP
dice `font-src 'self'`, sin un solo dominio de Google. Aquí se replica esa misma
propiedad (que el navegador del técnico no le pida nada a un tercero) con el
medio que este panel tiene: los bytes viajan en el código.

POR QUÉ EN BASE64 DENTRO DE UN .py Y NO COMO FICHERO. Un `.woff2` en disco habría
que meterlo en el bundle de Vercel a mano, y ese es exactamente el fallo de s326b
—`config/` llevaba desde #308 sin viajar, en silencio, porque `.vercelignore`
excluye todo y re-incluye a mano—. Un módulo Python viaja con el código por
construcción: no hay nada que recordar.

QUÉ SE INCRUSTA. El subconjunto `latin` del peso 400, RECORTADO a los catorce
glifos que la puerta pinta («Fontiber Bot PCI», con su espacio duro): **1.988
bytes**, frente a los ~38 KB del subconjunto latino completo y los ~110 KB de la
familia. Y viaja SOLO en la respuesta de `/entrar` — el resto del panel ni la
descarga ni abre su CSP.

LICENCIA. Playfair Display se distribuye bajo la **SIL Open Font License 1.1**,
que permite incrustarla. El aviso de copyright y la URL de la licencia viajan
DENTRO del propio fichero (`name` IDs 0 y 14), que es como la OFL pide que se
conserven:

    Copyright 2017 The Playfair Display Project Authors
    (https://github.com/clauseggers/Playfair-Display), with Reserved Font Name
    "Playfair Display".  ·  http://scripts.sil.org/OFL

CÓMO SE REGENERA (si algún día cambia el texto del logotipo):
`python -m scripts.s328c_recortar_fuente_marca`, que descarga el subconjunto
latino de Google, lo recorta al texto que se le pase y reescribe este módulo.
"""
from __future__ import annotations

#: Playfair Display 400, subconjunto de 14 glifos, woff2, en base64.
PLAYFAIR_PUERTA_B64 = (
    "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"
)

#: Los caracteres que el subconjunto REALMENTE cubre. Si el logotipo de la
#: puerta usa uno que no esté aquí, el navegador cae a la serif del sistema para
#: ESE carácter y el titular sale con dos tipografías. Lo cruza un test.
GLIFOS = " BCFIPbeinort\u00a0"
