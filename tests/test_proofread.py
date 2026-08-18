import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent
                       / "skills" / "hwpx-edit" / "scripts"))

import _hwpxlib as lib
from conftest import SECTION_XML

# 엔티티(&gt;, 숫자 참조)가 있는 별도 픽스처 — extract는 엔티티를 언이스케이프하지 않는다.
ENTITY_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    ' xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">'
    '<hp:p><hp:run><hp:t>조건 a&gt;b 그리고&#8203;됬다</hp:t></hp:run></hp:p>'
    '</hs:sec>'
)


def test_enumerate_matches_paragraph_texts_on_fixture():
    paras = lib.enumerate_body_paragraphs(SECTION_XML)
    assert [p["display"] for p in paras] == lib.paragraph_texts(SECTION_XML)
    # 메모 마스킹으로 [1]이 본문이어야 한다(메모 주석이 아니라).
    assert paras[1]["display"].startswith("앵커 본문을 이어서 쓴다.")


def test_enumerate_matches_paragraph_texts_with_entities():
    paras = lib.enumerate_body_paragraphs(ENTITY_XML)
    assert [p["display"] for p in paras] == lib.paragraph_texts(ENTITY_XML)
    # 엔티티는 언이스케이프되지 않고 원문 그대로 노출된다.
    assert paras[0]["display"] == "조건 a&gt;b 그리고&#8203;됬다"


def test_t_nodes_point_at_real_body_text():
    paras = lib.enumerate_body_paragraphs(SECTION_XML)
    # 문단 1의 어떤 t_node 안에 본문 "앵커 본문"이 있고, 메모 주석은 없어야 한다.
    joined = "".join(SECTION_XML[a:b] for a, b in paras[1]["t_nodes"])
    assert "앵커 본문" in joined
    assert "이건 메모 주석이다" not in joined
