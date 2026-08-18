import zipfile

from conftest import make_hwpx


def test_fixture_opens_and_mimetype_first_stored(sample_hwpx):
    with zipfile.ZipFile(sample_hwpx) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype"
        assert infos[0].compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/hwp+zip"
        assert "Contents/section0.xml" in z.namelist()
