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


import pytest


def test_apply_single_node_correction():
    out, res = lib.apply_paragraph_corrections(
        SECTION_XML, [{"p": 1, "old": "앵커 본문", "new": "기준 문장"}])
    assert "기준 문장" in out
    assert "앵커 본문" not in out
    assert res[0]["delta"] == len("기준 문장") - len("앵커 본문")
    assert lib.is_wellformed(out) is True
    # 다른 문단·하이퍼링크는 그대로.
    assert "첫 문단 본문이다." in out
    assert "링크텍스트" in out


def test_apply_rejects_memo_only_anchor():
    # 메모 주석 안에만 있는 문자열은 본문 t_node에 없다 → count 0.
    with pytest.raises(ValueError):
        lib.apply_paragraph_corrections(
            SECTION_XML, [{"p": 1, "old": "이건 메모 주석이다", "new": "x"}])


def test_apply_escapes_new_and_stays_wellformed():
    out, _ = lib.apply_paragraph_corrections(
        SECTION_XML, [{"p": 0, "old": "첫 문단 본문이다.", "new": "A < B & C > D"}])
    assert "&lt;" in out and "&amp;" in out and "&gt;" in out
    assert "A < B" not in out  # raw markup-breaking chars must be escaped
    assert lib.is_wellformed(out) is True


def test_apply_preserves_untouched_entities():
    # 같은 노드의 &gt; / &#8203; 는 인접 단어 교정 후에도 바이트 그대로 남는다.
    out, _ = lib.apply_paragraph_corrections(
        ENTITY_XML, [{"p": 0, "old": "됬다", "new": "됐다"}])
    assert "됐다" in out
    assert "&gt;" in out
    assert "&#8203;" in out
    assert lib.is_wellformed(out) is True


def test_apply_run_boundary_anchor_fails_safely():
    # "본문이다.앵커"처럼 t_node 경계를 넘는 old 는 단일 노드에 없다 → count 0.
    with pytest.raises(ValueError):
        lib.apply_paragraph_corrections(
            SECTION_XML, [{"p": 0, "old": "본문이다.앵커", "new": "x"}])


def test_apply_multiple_corrections_same_paragraph():
    out, res = lib.apply_paragraph_corrections(
        SECTION_XML, [
            {"p": 1, "old": "앵커 본문", "new": "기준 문장"},
            {"p": 1, "old": "링크텍스트", "new": "링크"},
        ])
    assert "기준 문장" in out and "링크" in out and "앵커 본문" not in out
    assert len(res) == 2
    assert lib.is_wellformed(out) is True


def test_apply_rejects_overlapping():
    xml = (
        '<hs:sec xmlns:hp="h" xmlns:hs="s"><hp:p><hp:run>'
        '<hp:t>Xabcd끝</hp:t></hp:run></hp:p></hs:sec>')
    with pytest.raises(ValueError):
        lib.apply_paragraph_corrections(
            xml, [{"p": 0, "old": "abc", "new": "1"},
                  {"p": 0, "old": "bcd", "new": "2"}])


def test_apply_input_validation():
    with pytest.raises(ValueError):   # empty
        lib.apply_paragraph_corrections(SECTION_XML, [])
    with pytest.raises(ValueError):   # old == ""
        lib.apply_paragraph_corrections(SECTION_XML, [{"p": 0, "old": "", "new": "x"}])
    with pytest.raises(ValueError):   # old == new
        lib.apply_paragraph_corrections(SECTION_XML, [{"p": 0, "old": "첫", "new": "첫"}])
    with pytest.raises(ValueError):   # duplicate record
        lib.apply_paragraph_corrections(
            SECTION_XML, [{"p": 0, "old": "첫 문단 본문이다.", "new": "a"},
                          {"p": 0, "old": "첫 문단 본문이다.", "new": "a"}])
    with pytest.raises(ValueError):   # p out of range
        lib.apply_paragraph_corrections(SECTION_XML, [{"p": 99, "old": "x", "new": "y"}])
    with pytest.raises(ValueError):   # negative p
        lib.apply_paragraph_corrections(SECTION_XML, [{"p": -1, "old": "x", "new": "y"}])
    with pytest.raises(ValueError):   # bool/float p
        lib.apply_paragraph_corrections(SECTION_XML, [{"p": True, "old": "x", "new": "y"}])
