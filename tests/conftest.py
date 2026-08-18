import zipfile
from pathlib import Path

import pytest

# Minimal but representative Contents/section0.xml:
# - two body paragraphs
# - one MEMO field (comment in subList) wrapping anchored text "앵커 본문"
# - one HYPERLINK field wrapping "링크텍스트"
# - one equation object (script "device _{key}")
# - one linesegarray to prove stripping works
SECTION_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
    ' xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">'
    '<hp:p><hp:run charPrIDRef="0"><hp:t>첫 문단 본문이다.</hp:t></hp:run>'
    '<hp:linesegarray><hp:lineseg textpos="0"/></hp:linesegarray></hp:p>'
    '<hp:p><hp:run charPrIDRef="0">'
    '<hp:ctrl><hp:fieldBegin id="1001" type="MEMO" editable="1">'
    '<hp:parameters cnt="1"><hp:stringParam name="ID">memo1</hp:stringParam></hp:parameters>'
    '<hp:subList><hp:p><hp:run><hp:t>이건 메모 주석이다</hp:t></hp:run></hp:p></hp:subList>'
    '</hp:fieldBegin></hp:ctrl>'
    '<hp:t>앵커 본문</hp:t>'
    '<hp:ctrl><hp:fieldEnd beginIDRef="1001"/></hp:ctrl>'
    '<hp:t>을 이어서 쓴다. </hp:t>'
    '<hp:ctrl><hp:fieldBegin id="2001" type="HYPERLINK"><hp:parameters cnt="0"/></hp:fieldBegin></hp:ctrl>'
    '<hp:t>링크텍스트</hp:t>'
    '<hp:ctrl><hp:fieldEnd beginIDRef="2001"/></hp:ctrl>'
    '<hp:equation id="3001"><hp:script>device _{key}</hp:script></hp:equation>'
    '<hp:t>로 끝난다.</hp:t></hp:run></hp:p>'
    '</hs:sec>'
)

# Minimal 1x1 PNG (stored raw), used for BinData/image1.png
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6360000002000100" "05000100" "0d0a2db4" "0000000049454e44ae426082"
)


def make_hwpx(dir_path, section_xml=SECTION_XML):
    """Write a minimal valid .hwpx and return its path.

    mimetype is written first and STORED (uncompressed); everything else deflated.
    No directory entries are added.
    """
    out = Path(dir_path) / "sample.hwpx"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/hwp+zip")
        z.writestr("version.xml", '<?xml version="1.0"?><version/>')
        z.writestr("Contents/section0.xml", section_xml)
        z.writestr("BinData/image1.png", PNG_1x1)
    return str(out)


@pytest.fixture
def sample_hwpx(tmp_path):
    return make_hwpx(tmp_path)
