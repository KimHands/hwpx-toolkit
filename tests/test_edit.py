import pytest

import _hwpxlib as lib
from conftest import SECTION_XML


def test_apply_replacements_unique_and_delta():
    out, res = lib.apply_replacements(
        SECTION_XML, [("첫 문단 본문이다.", "첫 문단 본문이 조금 늘었다.")])
    assert "첫 문단 본문이 조금 늘었다." in out
    assert res[0]["delta"] == len("첫 문단 본문이 조금 늘었다.") - len("첫 문단 본문이다.")


def test_apply_replacements_rejects_non_unique():
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [("<hp:t>", "<hp:t>")])  # appears many times


def test_apply_replacements_rejects_absent():
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [("존재하지않는문자열", "x")])


@pytest.mark.parametrize("anchor", ["device _{key}", "메모 주석", 'type="MEMO"'])
def test_apply_replacements_rejects_anchor_outside_body_text(anchor):
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [(anchor, "x")])


def test_apply_replacements_counts_only_body_text():
    xml = SECTION_XML.replace("첫 문단 본문이다.", "메모 주석 인용")
    out, _ = lib.apply_replacements(xml, [("메모 주석", "인용문")])
    assert "인용문 인용" in out
    assert "이건 메모 주석이다" in out


def test_apply_replacements_escapes_new_text():
    out, _ = lib.apply_replacements(SECTION_XML, [("첫 문단", "<hp:x>A&B</hp:x>")])
    assert "<hp:x>" not in out
    assert "&lt;hp:x&gt;A&amp;B&lt;/hp:x&gt;" in out
    assert lib.is_wellformed(out) is True


def test_apply_replacements_rejects_empty_anchor():
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [("", "x")])


def test_apply_replacements_supports_temp_token_chaining():
    xml = SECTION_XML.replace("첫 문단 본문이다.", "[10] 그리고 [11]")
    out, _ = lib.apply_replacements(xml, [
        ("[10]", "[T11]"), ("[11]", "[T12]"), ("[T11]", "[11]"), ("[T12]", "[12]")])
    assert "[11] 그리고 [12]" in out
