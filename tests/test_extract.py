import _hwpxlib as lib
from conftest import SECTION_XML


def test_read_section(sample_hwpx):
    xml = lib.read_section(sample_hwpx)
    assert "Contents" not in xml  # it's the section content, not a path
    assert "<hp:t>첫 문단 본문이다.</hp:t>" in xml


def test_plain_text_drops_memo_comment_marks_equation():
    txt = lib.plain_text(SECTION_XML)
    assert "이건 메모 주석이다" not in txt      # memo comment removed
    assert "앵커 본문" in txt                    # anchored body kept
    assert "링크텍스트" in txt                   # hyperlink text kept
    assert "⟨식⟩" in txt                         # equation marked
    assert "device _{key}" not in txt            # raw script not in body


def test_paragraph_texts():
    paras = lib.paragraph_texts(SECTION_XML)
    assert paras[0] == "첫 문단 본문이다."
    assert paras[1].startswith("앵커 본문을 이어서 쓴다. 링크텍스트⟨식⟩로 끝난다.")


def test_list_equations():
    eqs = lib.list_equations(SECTION_XML)
    assert eqs["device _{key}"] == 1
