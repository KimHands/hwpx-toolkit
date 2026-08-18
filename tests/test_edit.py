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
