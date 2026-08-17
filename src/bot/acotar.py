# -*- coding: utf-8 -*-
"""Respuestas que NO caben: recortar diciéndolo, y ofrecer cómo pedir el resto.

Adjudicación de Alberto (17-ago, s324f), literal: «puede ser generalizable a
preguntas en las que la respuesta no quepa, para facilitar que el usuario haga un
follow-up, además de incluir un mensaje de limitación en caso de llegar a dicho
límite para que el usuario lo entienda».

EL PROBLEMA REAL. Telegram corta en 4.096 caracteres y el bot tiene listas que no
caben (756 modelos, ~30 fabricantes con sus conteos). Hay dos formas malas de
tratarlo y las dos han existido aquí: reventar el mensaje —un `BadRequest` y el
técnico no recibe NADA (dúo H1, s322)— o recortar en silencio, que es peor porque
el técnico se lleva una lista incompleta creyéndola completa. Un catálogo que
enseña 22 de 756 productos sin decirlo no es una respuesta corta: es una respuesta
falsa.

LA DECISIÓN DE DISEÑO, y es la única que importa aquí: **el aviso de recorte se
genera DENTRO de esta función, y su espacio se reserva ANTES de colocar ningún
elemento.** Escribirlo como una llamada aparte —«acota, y luego avisa si hace
falta»— convierte el aviso en algo que se puede olvidar, y en algo que se queda
fuera justo cuando más falta hace: cuando no cabe. Aquí no hay forma de recortar
sin avisar, porque es la misma operación.

HOJA PURA a propósito: entra una lista de textos y sale un texto. Sin red, sin
entorno, sin Telegram y sin saber qué son los elementos. Se prueba con una tabla
de casos y sirve a cualquier respuesta futura que no quepa, no sólo al catálogo.

Los tres consumidores para los que nace (declarados, no hipotéticos): la lista de
fabricantes, el catálogo por marca, y el inventario agrupado —que hoy implementa
este mismo patrón a mano, dos veces («…y N categorías más», «…y N más»)—.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Cota por defecto. Telegram admite 4.096 caracteres; se deja margen para el
#: marcado y para que un carácter multibyte no acerque el borde sin avisar.
PRESUPUESTO_DEFECTO = 3500


@dataclass(frozen=True)
class Acotado:
    """El resultado: el texto listo para enviar y cuánto se dejó fuera."""

    texto: str
    mostrados: int
    total: int

    @property
    def recortado(self) -> bool:
        return self.mostrados < self.total


def _aviso(omitidos: int, plural: str) -> str:
    """El mensaje de limitación. Dice QUÉ falta y POR QUÉ falta — un «…y 534 más»
    a secas informa del número pero deja al lector pensando si el bot no tiene el
    resto o no ha querido enseñarlo."""
    unidad = plural if omitidos != 1 else plural.rstrip("s")
    return (f"⚠️ Faltan {omitidos} {unidad} por mostrar: no caben en un solo "
            f"mensaje.")


def acotar(
    elementos: list[str],
    *,
    presupuesto: int = PRESUPUESTO_DEFECTO,
    encabezado: str = "",
    coletilla: str = "",
    plural: str = "elementos",
) -> Acotado:
    """Compone `encabezado` + tantos `elementos` como quepan + aviso + `coletilla`.

    El orden del cálculo ES el contrato: se descuenta primero lo que SIEMPRE va
    (encabezado, coletilla) y lo que iría **si hubiera recorte** (el aviso), y sólo
    el resto se reparte entre los elementos. Reservar el aviso por adelantado
    cuesta unos caracteres cuando al final no hace falta, y a cambio hace
    imposible el caso que importa: quedarse sin sitio justo para la línea que
    explica que no había sitio.

    La `coletilla` se devuelve SIEMPRE, quepa todo o no: es la que facilita el
    follow-up («pregúntame por una marca»), y es útil también cuando la respuesta
    está completa.
    """
    total = len(elementos)
    partes_fijas = [p for p in (encabezado, coletilla) if p]
    # 2 saltos de línea entre bloques; el aviso, si aparece, suma otro bloque.
    coste_fijo = sum(len(p) for p in partes_fijas) + 2 * len(partes_fijas)
    reserva_aviso = len(_aviso(total, plural)) + 2 if total else 0

    disponible = presupuesto - coste_fijo - reserva_aviso
    escogidos: list[str] = []
    usado = 0
    for e in elementos:
        coste = len(e) + (1 if escogidos else 0)      # 1 = el salto de línea
        if usado + coste > disponible:
            break
        escogidos.append(e)
        usado += coste

    bloques: list[str] = []
    if encabezado:
        bloques.append(encabezado)
    if escogidos:
        bloques.append("\n".join(escogidos))
    if len(escogidos) < total:
        bloques.append(_aviso(total - len(escogidos), plural))
    if coletilla:
        bloques.append(coletilla)

    return Acotado(texto="\n\n".join(bloques), mostrados=len(escogidos),
                   total=total)
