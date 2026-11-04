import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from conftest import make_hwpx

CLI = str(Path(__file__).resolve().parent.parent
          / "skills" / "hwpx-edit" / "scripts" / "hwpx.py")


def run(*args, env=None):
    return subprocess.run([sys.executable, CLI, *args],
                          capture_output=True, encoding="utf-8", env=env)


def legacy_codec_env(codec):
    return {**os.environ, "PYTHONIOENCODING": codec}


@pytest.mark.parametrize("codec", ["cp949", "cp1252"])
def test_extract_stdout_is_utf8_under_legacy_codec(sample_hwpx, codec):
    r = run("extract", sample_hwpx, "--paragraphs", env=legacy_codec_env(codec))
    assert r.returncode == 0
    assert "첫 문단 본문이다." in r.stdout
    assert "⟨식⟩" in r.stdout


@pytest.mark.parametrize("codec", ["cp949", "cp1252"])
def test_error_stderr_is_utf8_under_legacy_codec(tmp_path, codec):
    src = make_hwpx(tmp_path)
    corr = tmp_path / "c.json"
    corr.write_text(json.dumps([{"p": 0, "old": "존재하지않음", "new": "x"}]),
                    encoding="utf-8")
    r = run("proofread", "apply", src, "-o", str(tmp_path / "x.hwpx"),
            "--from", str(corr), env=legacy_codec_env(codec))
    assert r.returncode == 2
    assert "존재하지않음" in r.stderr


def test_extract_paragraphs(sample_hwpx):
    r = run("extract", sample_hwpx, "--paragraphs")
    assert r.returncode == 0
    assert "첫 문단 본문이다." in r.stdout


def test_memo_clear(tmp_path):
    src = make_hwpx(tmp_path)
    out = str(tmp_path / "nomemo.hwpx")
    r = run("memo", "clear", src, "-o", out)
    assert r.returncode == 0
    xml = zipfile.ZipFile(out).read("Contents/section0.xml").decode("utf-8")
    assert 'type="MEMO"' not in xml
    assert "앵커 본문" in xml
    assert 'type="HYPERLINK"' in xml
    assert "<hp:linesegarray" not in xml   # stripped


def test_edit_reports_delta(tmp_path):
    src = make_hwpx(tmp_path)
    out = str(tmp_path / "edited.hwpx")
    r = run("edit", src, "-o", out,
            "--replace", "첫 문단 본문이다.\t첫 문단 본문이 늘었다.")
    assert r.returncode == 0
    assert "delta" in r.stdout.lower() or "+" in r.stdout


def test_edit_rejects_non_unique(tmp_path):
    src = make_hwpx(tmp_path)
    out = str(tmp_path / "x.hwpx")
    r = run("edit", src, "-o", out, "--replace", "<hp:t>\t<hp:t>")
    assert r.returncode != 0
    assert not Path(out).exists()


def test_verify(sample_hwpx):
    r = run("verify", sample_hwpx)
    assert r.returncode == 0
    assert "wellformed" in r.stdout.lower() or "True" in r.stdout


def test_figure_swap(tmp_path):
    from conftest import PNG_1x1
    src = make_hwpx(tmp_path)
    out = str(tmp_path / "swapped.hwpx")
    # Write a distinct replacement PNG (flip one byte so bytes differ from original)
    replacement_png = bytearray(PNG_1x1)
    replacement_png[-1] ^= 0xFF
    replacement_png = bytes(replacement_png)
    png_path = str(tmp_path / "new.png")
    Path(png_path).write_bytes(replacement_png)

    r = run("figure", "swap", src, "-o", out, "--slot", "image1", "--png", png_path)
    assert r.returncode == 0
    assert Path(out).exists()
    # OUT must differ from SRC
    assert Path(out).read_bytes() != Path(src).read_bytes()
    # Swapped bytes must be present in OUT's BinData/image1.png
    with zipfile.ZipFile(out) as z:
        assert z.read("BinData/image1.png") == replacement_png
    # SRC must be unchanged
    with zipfile.ZipFile(src) as z:
        assert z.read("BinData/image1.png") == PNG_1x1


def test_proofread_apply(tmp_path):
    src = make_hwpx(tmp_path)
    corr = tmp_path / "c.json"
    corr.write_text(json.dumps(
        [{"p": 0, "old": "첫 문단 본문이다.", "new": "첫 문단 본문이 늘었다."}]),
        encoding="utf-8")
    out = str(tmp_path / "pf.hwpx")
    r = run("proofread", "apply", src, "-o", out, "--from", str(corr))
    assert r.returncode == 0
    xml = zipfile.ZipFile(out).read("Contents/section0.xml").decode("utf-8")
    assert "첫 문단 본문이 늘었다." in xml
    assert "<hp:linesegarray" not in xml           # stripped
    # 입력 파일은 불변.
    src_xml = zipfile.ZipFile(src).read("Contents/section0.xml").decode("utf-8")
    assert "첫 문단 본문이다." in src_xml


def test_proofread_check_writes_nothing(tmp_path):
    src = make_hwpx(tmp_path)
    corr = tmp_path / "c.json"
    corr.write_text(json.dumps(
        [{"p": 0, "old": "첫 문단 본문이다.", "new": "바뀐 문단이다."}]),
        encoding="utf-8")
    out = str(tmp_path / "nope.hwpx")
    r = run("proofread", "apply", src, "-o", out, "--from", str(corr), "--check")
    assert r.returncode == 0
    assert not Path(out).exists()


def test_proofread_missing_from_file(tmp_path):
    src = make_hwpx(tmp_path)
    out = str(tmp_path / "x.hwpx")
    r = run("proofread", "apply", src, "-o", out, "--from",
            str(tmp_path / "absent.json"))
    assert r.returncode == 2
    assert not Path(out).exists()


def test_proofread_bad_match_exits_2(tmp_path):
    src = make_hwpx(tmp_path)
    corr = tmp_path / "c.json"
    corr.write_text(json.dumps([{"p": 0, "old": "존재하지않음", "new": "x"}]),
                    encoding="utf-8")
    out = str(tmp_path / "x.hwpx")
    r = run("proofread", "apply", src, "-o", out, "--from", str(corr))
    assert r.returncode == 2
    assert not Path(out).exists()


def test_figure_swap_missing_slot_exits_2(tmp_path):
    from conftest import PNG_1x1
    src = make_hwpx(tmp_path)
    png = tmp_path / "new.png"
    png.write_bytes(PNG_1x1)
    out = tmp_path / "x.hwpx"
    r = run("figure", "swap", src, "-o", str(out), "--slot", "image99", "--png", str(png))
    assert r.returncode == 2
    assert "image99" in r.stderr
    assert not out.exists()


def test_repackage_malformed_xml_exits_2(tmp_path):
    src = make_hwpx(tmp_path)
    bad = tmp_path / "bad.xml"
    bad.write_text("<broken", encoding="utf-8")
    out = tmp_path / "x.hwpx"
    r = run("repackage", "--original", src, "-o", str(out),
            "--replace", "Contents/section0.xml=%s" % bad)
    assert r.returncode == 2
    assert not out.exists()


def test_same_input_output_path_reports_error_without_traceback(tmp_path):
    src = make_hwpx(tmp_path)
    r = run("memo", "clear", src, "-o", src)
    assert r.returncode == 2
    assert r.stderr.startswith("error:")
    assert "Traceback" not in r.stderr


def test_missing_input_exits_2(tmp_path):
    r = run("extract", str(tmp_path / "absent.hwpx"))
    assert r.returncode == 2
    assert "Traceback" not in r.stderr


def test_non_zip_input_exits_2(tmp_path):
    bad = tmp_path / "bad.hwpx"
    bad.write_text("not a zip", encoding="utf-8")
    r = run("extract", str(bad))
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
