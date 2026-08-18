import subprocess
import sys
import zipfile
from pathlib import Path

from conftest import make_hwpx

CLI = str(Path(__file__).resolve().parent.parent
          / "skills" / "hwpx-edit" / "scripts" / "hwpx.py")


def run(*args):
    return subprocess.run([sys.executable, CLI, *args],
                          capture_output=True, text=True)


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
