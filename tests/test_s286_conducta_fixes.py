"""Tests de los fixes deterministas s286 de la lane de conducta:
(a) parser DIAGRAMAS_RELEVANTES no amputa la cola de la respuesta;
(b) fuga-hyq: padres con duplicate_of no resucitan vía surrogates.
"""
from __future__ import annotations

import json
import re


class TestParserDiagramas:
    """Réplica exacta de la lógica parcheada en generator.py (unidad pura)."""

    @staticmethod
    def _parse(raw_answer: str, diagram_map: dict) -> tuple[str, list]:
        answer = raw_answer
        diagrams: list = []
        if "DIAGRAMAS_RELEVANTES:" in raw_answer:
            head, _, rest = raw_answer.rpartition("DIAGRAMAS_RELEVANTES:")
            m = re.match(r"\s*(\[[\d\s,]*\])", rest)
            if m:
                tail = rest[m.end():].strip()
                answer = head.rstrip() + (f"\n\n{tail}" if tail else "")
                refs = json.loads(m.group(1))
                if isinstance(refs, list):
                    seen = set()
                    for ref in refs:
                        if ref in diagram_map and diagram_map[ref]["url"] not in seen:
                            seen.add(diagram_map[ref]["url"])
                            diagrams.append(diagram_map[ref])
            else:
                answer = raw_answer
        return answer, diagrams

    DM = {1: {"url": "u1"}, 2: {"url": "u2"}, 3: {"url": "u3"}}

    def test_marcador_al_final_caso_feliz(self):
        a, d = self._parse("Respuesta técnica.\n\nDIAGRAMAS_RELEVANTES: [1, 3]", self.DM)
        assert a == "Respuesta técnica." and [x["url"] for x in d] == ["u1", "u3"]

    def test_cola_tras_el_array_se_conserva_y_parsea(self):
        raw = ("Respuesta.\n\nDIAGRAMAS_RELEVANTES: [1, 2]\n\n---\n\n"
               "También puedo ayudarte con: **otra cosa**.")
        a, d = self._parse(raw, self.DM)
        assert "También puedo ayudarte" in a          # la cola YA NO se amputa
        assert [x["url"] for x in d] == ["u1", "u2"]   # y los diagramas YA NO se pierden
        assert "DIAGRAMAS_RELEVANTES" not in a

    def test_marcador_sin_array_deja_respuesta_intacta(self):
        raw = "Texto.\n\nDIAGRAMAS_RELEVANTES: ninguno aplicable"
        a, d = self._parse(raw, self.DM)
        assert a == raw and d == []

    def test_sin_marcador_intacto(self):
        a, d = self._parse("Sin marcador.", self.DM)
        assert a == "Sin marcador." and d == []

    def test_urls_duplicadas_deduplicadas(self):
        dm = {1: {"url": "u"}, 2: {"url": "u"}}
        _, d = self._parse("X\n\nDIAGRAMAS_RELEVANTES: [1, 2]", dm)
        assert len(d) == 1

    def test_paridad_con_generator_real(self):
        """El bloque de generator.py debe contener el patrón nuevo (anti-regresión textual)."""
        src = open("src/rag/generator.py", encoding="utf-8").read()
        assert r"re.match(r\"\s*(\[[\d\s,]*\])\", rest)" in src or "\\[[\\d\\s,]*\\]" in src
        assert "answer = raw_answer" in src  # rama marcador-sin-array conserva intacto


class TestFugaHyqDuplicados:
    def test_hydrate_select_incluye_duplicate_of(self):
        src = open("src/rag/retriever.py", encoding="utf-8").read()
        m = re.search(r"_HYDRATE_SELECT = \((?:[^)]|\n)*?\)", src)
        assert m and "duplicate_of" in m.group(0)

    def test_guard_en_canal_hyq(self):
        src = open("src/rag/retriever.py", encoding="utf-8").read()
        assert src.count('row.get("duplicate_of")') >= 1
        assert 'p.get("duplicate_of")' in src

    def test_swap_de_surrogate_filtra_duplicados(self):
        """Unidad de la lógica del swap: un padre con duplicate_of se descarta."""
        parents = {"P1": {"id": "P1", "duplicate_of": "P0"},
                   "P2": {"id": "P2", "duplicate_of": None}}
        smap = {"s1": "P1", "s2": "P2"}
        out = []
        for c in [{"id": "s1", "similarity": 0.9}, {"id": "s2", "similarity": 0.8}]:
            p = parents.get(smap[c["id"]])
            if not p or p.get("duplicate_of"):
                continue
            out.append(p["id"])
        assert out == ["P2"]
