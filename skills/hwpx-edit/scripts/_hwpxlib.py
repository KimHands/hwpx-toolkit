"""hwpx-toolkit core library (stdlib only)."""
__version__ = "0.1.0"

import re
import zipfile
import collections

SECTION_PATH = "Contents/section0.xml"

_MEMO_SUBLIST = re.compile(
    r'<hp:fieldBegin[^>]*type="MEMO".*?</hp:fieldBegin>', re.S)
_EQUATION = re.compile(r'<hp:equation\b.*?</hp:equation>', re.S)
_T = re.compile(r'<hp:t>(.*?)</hp:t>', re.S)
_P = re.compile(r'<hp:p\b.*?</hp:p>', re.S)
_SCRIPT = re.compile(r'<hp:script>(.*?)</hp:script>', re.S)


def read_section(hwpx_path):
    with zipfile.ZipFile(hwpx_path) as z:
        return z.read(SECTION_PATH).decode("utf-8")


def strip_memo_sublists(xml):
    # Remove the entire MEMO fieldBegin element (its subList holds the comment).
    return _MEMO_SUBLIST.sub("", xml)


def plain_text(xml, eq_marker="⟨식⟩"):
    body = strip_memo_sublists(xml)
    # Wrap equation marker in hp:t tags so it gets extracted with other text
    body = _EQUATION.sub(f"<hp:t>{eq_marker}</hp:t>", body)
    return "".join(_T.findall(body))


def paragraph_texts(xml, eq_marker="⟨식⟩"):
    body = strip_memo_sublists(xml)
    # Wrap equation marker in hp:t tags so it gets extracted with other text
    body = _EQUATION.sub(f"<hp:t>{eq_marker}</hp:t>", body)
    out = []
    for p in _P.findall(body):
        t = "".join(_T.findall(p)).strip()
        if t:
            out.append(t)
    return out


def list_equations(xml):
    return collections.Counter(_SCRIPT.findall(xml))
