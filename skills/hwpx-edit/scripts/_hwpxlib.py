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


import xml.dom.minidom as _minidom

_LINESEG = re.compile(r'<hp:linesegarray>.*?</hp:linesegarray>', re.S)
_LINESEG_SELF = re.compile(r'<hp:linesegarray\s*/>')
_FIELDBEGIN_TYPE = re.compile(r'<hp:fieldBegin[^>]*type="([A-Z]+)"')
_EQ_ID = re.compile(r'<hp:equation\s+id="(\d+)"')


def strip_linesegarray(xml):
    xml = _LINESEG.sub("", xml)
    xml = _LINESEG_SELF.sub("", xml)
    return xml


def is_wellformed(xml):
    try:
        _minidom.parseString(xml)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("XML is not well-formed: %s" % exc)
    return True


def repackage(original_path, out_path, replacements):
    with zipfile.ZipFile(original_path, "r") as zin, \
            zipfile.ZipFile(out_path, "w") as zout:
        for item in zin.infolist():
            data = replacements.get(item.filename)
            if data is None:
                data = zin.read(item.filename)
            zi = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            zi.compress_type = item.compress_type
            zi.external_attr = item.external_attr
            zi.internal_attr = item.internal_attr
            zi.create_system = item.create_system
            zout.writestr(zi, data)


def verify(hwpx_path):
    xml = read_section(hwpx_path)
    try:
        wellformed = is_wellformed(xml)
    except ValueError:
        wellformed = False
    types = _FIELDBEGIN_TYPE.findall(xml)
    ids = _EQ_ID.findall(xml)
    seen, dup = set(), []
    for i in ids:
        if i in seen:
            dup.append(i)
        seen.add(i)
    return {
        "wellformed": wellformed,
        "linesegarray": len(_LINESEG.findall(xml)) + len(_LINESEG_SELF.findall(xml)),
        "memo_fields": types.count("MEMO"),
        "hyperlink_fields": types.count("HYPERLINK"),
        "dup_equation_ids": dup,
    }
