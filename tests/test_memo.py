import _hwpxlib as lib
from conftest import SECTION_XML

# Section XML with reversed attribute order: type="MEMO" appears BEFORE id=
SECTION_XML_REVERSED_ATTRS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    ' xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">'
    '<hp:p><hp:run charPrIDRef="0"><hp:t>본문이다.</hp:t></hp:run></hp:p>'
    '<hp:p><hp:run charPrIDRef="0">'
    '<hp:ctrl><hp:fieldBegin type="MEMO" id="9001" editable="1">'
    '<hp:parameters cnt="1"><hp:stringParam name="ID">memo1</hp:stringParam></hp:parameters>'
    '<hp:subList><hp:p><hp:run><hp:t>역순 메모</hp:t></hp:run></hp:p></hp:subList>'
    '</hp:fieldBegin></hp:ctrl>'
    '<hp:t>앵커텍스트</hp:t>'
    '<hp:ctrl><hp:fieldEnd beginIDRef="9001"/></hp:ctrl>'
    '</hp:run></hp:p>'
    '</hs:sec>'
)


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


def test_remove_memos_reversed_attr_order():
    """remove_memos must work when type="MEMO" precedes id= in fieldBegin."""
    out, n = lib.remove_memos(SECTION_XML_REVERSED_ATTRS)
    assert n == 1
    assert 'type="MEMO"' not in out
    assert "역순 메모" not in out
    assert "앵커텍스트" in out
    # No orphaned fieldEnd must remain
    assert 'beginIDRef="9001"' not in out
    assert lib.is_wellformed(out) is True
