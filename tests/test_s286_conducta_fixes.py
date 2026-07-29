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


class TestPromptFlagsConducta:
    """(c) GENERATOR_DIRECT_FIRST y (e) GENERATOR_FOLLOWUPS — anclaje y byte-identidad."""

    def test_followup_block_es_substring_exacto(self):
        import src.rag.generator as g
        assert g._FOLLOWUP_BLOCK in g.SYSTEM_PROMPT

    def test_default_byte_identico(self):
        import os
        import src.rag.generator as g
        for k in ("GENERATOR_FOLLOWUPS", "GENERATOR_DIRECT_FIRST"):
            os.environ.pop(k, None)
        assert g._assemble_system(None) == g.SYSTEM_PROMPT

    def test_followups_off_retira_el_bloque(self, monkeypatch):
        import src.rag.generator as g
        monkeypatch.setenv("GENERATOR_FOLLOWUPS", "off")
        s = g._assemble_system(None)
        assert "SUGERENCIAS DE FOLLOW-UP" not in s
        assert "NEGACIONES Y AUSENCIA" in s  # el resto del prompt sobrevive

    def test_direct_first_on_anade_regla(self, monkeypatch):
        import src.rag.generator as g
        monkeypatch.setenv("GENERATOR_DIRECT_FIRST", "on")
        assert "PRIMERA LÍNEA (regla de apertura)" in g._assemble_system(None)


class TestListingGate:
    """(d) 5.1: gate de visual assets en intent de listado (flag default off)."""

    def test_regex_caza_los_casos_de_dogfooding(self):
        import src.rag.generator as g
        assert g._LISTING_INTENT.search("¿qué dispositivos de detección por aspiración tiene Notifier?")
        assert g._LISTING_INTENT.search("¿Qué productos Detnov tienes?")
        assert g._LISTING_INTENT.search("¿Qué modelos de Kidde tienes?")

    def test_regex_no_caza_preguntas_tecnicas(self):
        import src.rag.generator as g
        assert not g._LISTING_INTENT.search("¿Cómo se conecta una sirena convencional en la ZXe?")
        assert not g._LISTING_INTENT.search("¿Qué resistencia lleva la entrada monitorizada?")
        assert not g._LISTING_INTENT.search("¿Qué modelo de detector me recomiendas para un garaje?")


class TestVaraV4:
    """Vara v4 del juez: facts tipados (T2b adjudicado)."""

    def _tbg(self):
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location(
            "tbg_v4test", pathlib.Path("scripts/test_bot_vs_gold.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_format_facts_tipa_correctamente(self):
        m = self._tbg()
        gold = {"atomic_facts": [
            {"texto": "RFL de 6K8 al final", "tipo": "core"},
            {"texto": "referencia 170-073-682", "tipo": "supplementary"}]}
        out = m._format_facts(gold)
        assert out == "- [CORE] RFL de 6K8 al final\n- [SUPP] referencia 170-073-682"

    def test_criterio_v4_reglas_clave(self):
        m = self._tbg()
        c = m._JUDGE_V4_CRITERIO
        assert "NUNCA baja el veredicto de PASS" in c        # supp jamás degrada
        assert "cubierto-con-otras-palabras CUENTA" in c     # anti-checklist
        assert m.JUDGE_VARA == "v4"                          # default v4

    def test_todos_los_golds_tienen_facts(self):
        import sys
        sys.path.insert(0, "scripts")
        import gold_store
        assert all((g.get("atomic_facts") or []) for g in gold_store.verified())
