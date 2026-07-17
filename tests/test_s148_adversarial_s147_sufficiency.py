from __future__ import annotations

from scripts.s148_adversarial_s147_sufficiency import build_packet


def test_s148_packet_is_blind_and_reconstructs_all_s147_questions() -> None:
    packet = build_packet()
    assert len(packet["questions"]) == 14
    assert packet["blind"]["authored_answer_points_included"] is False
    assert packet["blind"]["s147_metrics_included"] is False
    assert len({row["question_id"] for row in packet["questions"]}) == 14
    assert all(row["selected_evidence"] for row in packet["questions"])
    assert all("answer_points" not in row for row in packet["questions"])
