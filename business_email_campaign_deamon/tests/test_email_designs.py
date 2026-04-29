from pathlib import Path


BLUEPRINT_DIR = Path(__file__).resolve().parents[1]
DESIGNS_DIR = BLUEPRINT_DIR / "input" / "designs"


def test_design_templates_use_children_book_palette():
    card = (DESIGNS_DIR / "card_email.html").read_text()
    reply = (DESIGNS_DIR / "personal_reply.html").read_text()

    for source in (card, reply):
        assert "#f24f5f" in source
        assert "#ffcf33" in source
        assert "#2f86c6" in source
        assert "#ecebe7" not in source

    assert "Story moments to explore" in card
    assert "A small story can make a big feeling easier to talk about." in reply


def test_payload_design_copies_match_root_designs():
    root_card = (DESIGNS_DIR / "card_email.html").read_text()
    root_reply = (DESIGNS_DIR / "personal_reply.html").read_text()
    copied_designs = sorted((BLUEPRINT_DIR / "payloads").glob("*/input/designs"))

    assert copied_designs
    for designs_dir in copied_designs:
        assert (designs_dir / "card_email.html").read_text() == root_card
        assert (designs_dir / "personal_reply.html").read_text() == root_reply
