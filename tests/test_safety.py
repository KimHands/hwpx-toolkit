import zipfile

import _hwpxlib as lib
from conftest import make_hwpx, SECTION_XML


def test_strip_linesegarray():
    assert "<hp:linesegarray" in SECTION_XML
    out = lib.strip_linesegarray(SECTION_XML)
    assert "<hp:linesegarray" not in out
    assert "첫 문단 본문이다." in out  # body untouched


def test_is_wellformed_ok():
    assert lib.is_wellformed(SECTION_XML) is True


def test_is_wellformed_raises():
    import pytest
    with pytest.raises(ValueError):
        lib.is_wellformed("<a><b></a>")


def test_repackage_preserves_structure(tmp_path):
    src = make_hwpx(tmp_path)
    new_section = SECTION_XML.replace("첫 문단 본문이다.", "바뀐 문단이다.")
    out = str(tmp_path / "out.hwpx")
    lib.repackage(src, out, {"Contents/section0.xml": new_section.encode("utf-8")})
    with zipfile.ZipFile(out) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype"
        assert infos[0].compress_type == zipfile.ZIP_STORED
        assert z.read("Contents/section0.xml").decode("utf-8") == new_section
        # no directory entries
        assert all(not i.filename.endswith("/") for i in infos)


def test_verify(tmp_path):
    src = make_hwpx(tmp_path)
    report = lib.verify(src)
    assert report["wellformed"] is True
    assert report["linesegarray"] == 1
    assert report["memo_fields"] == 1
    assert report["hyperlink_fields"] == 1
    assert report["dup_equation_ids"] == []
