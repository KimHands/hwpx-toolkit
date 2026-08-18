import _hwpxlib as lib
from conftest import SECTION_XML


def test_list_memos():
    memos = lib.list_memos(SECTION_XML)
    assert len(memos) == 1
    assert memos[0]["id"] == "memo1"
    assert memos[0]["comment"] == "이건 메모 주석이다"


def test_remove_memos_keeps_body_and_hyperlink():
    out, n = lib.remove_memos(SECTION_XML)
    assert n == 1
    assert 'type="MEMO"' not in out
    assert "이건 메모 주석이다" not in out       # comment gone
    assert "앵커 본문" in out                     # anchored body kept
    assert 'type="HYPERLINK"' in out              # hyperlink preserved
    assert "링크텍스트" in out
    assert lib.is_wellformed(out) is True
