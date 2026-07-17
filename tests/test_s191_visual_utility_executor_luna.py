import base64

from scripts.s191_visual_utility_executor_luna import _input_content


def test_luna_input_binds_each_item_to_one_low_detail_image(monkeypatch):
    monkeypatch.setattr(
        "scripts.s191_visual_utility_executor_luna._thumbnail", lambda value: value
    )
    content = _input_content(
        [{"item_id": "i1"}, {"item_id": "i2"}], [b"one", b"two"]
    )

    assert [part["type"] for part in content] == [
        "input_text",
        "input_text",
        "input_image",
        "input_text",
        "input_image",
    ]
    assert content[1]["text"] == "ITEM i1"
    assert content[2]["detail"] == "low"
    assert content[2]["image_url"].endswith(base64.b64encode(b"one").decode("ascii"))
