"""hwpx-toolkit core library (stdlib only)."""
__version__ = "0.1.0"

import re
import zipfile
import collections
import struct
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

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
    if Path(out_path).resolve() == Path(original_path).resolve():
        raise ValueError("out_path must differ from original_path (never modify input in place)")
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


_MEMO_FIELD = re.compile(
    r'<hp:ctrl><hp:fieldBegin[^>]*type="MEMO".*?</hp:fieldBegin></hp:ctrl>', re.S)
_MEMO_FIELDBEGIN_TAG = re.compile(r'<hp:fieldBegin\b[^>]*type="MEMO"[^>]*>')
_ID_ATTR = re.compile(r'\bid="(\d+)"')
_PARAM_ID = re.compile(r'name="ID">([^<]*)</hp:stringParam>')
_PARAM_AUTHOR = re.compile(r'name="Author">([^<]*)</hp:stringParam>')


def list_memos(xml):
    out = []
    for m in re.finditer(
            r'<hp:fieldBegin[^>]*type="MEMO".*?</hp:fieldBegin>', xml, re.S):
        block = m.group(0)
        pid = _PARAM_ID.search(block)
        author = _PARAM_AUTHOR.search(block)
        sub = re.search(r'<hp:subList>.*?</hp:subList>', block, re.S)
        comment = "".join(_T.findall(sub.group(0))) if sub else ""
        out.append({
            "id": pid.group(1) if pid else "",
            "author": author.group(1) if author else None,
            "comment": comment,
        })
    return out


def remove_memos(xml):
    memo_ids = [
        _ID_ATTR.search(tag).group(1)
        for tag in _MEMO_FIELDBEGIN_TAG.findall(xml)
        if _ID_ATTR.search(tag)
    ]
    new_xml, n = _MEMO_FIELD.subn("", xml)
    for mid in memo_ids:
        pat = r'<hp:ctrl><hp:fieldEnd beginIDRef="%s"[^>]*/></hp:ctrl>' % re.escape(mid)
        new_xml = re.sub(pat, "", new_xml)
    return new_xml, n


def apply_replacements(xml, pairs):
    results = []
    for old, new in pairs:
        count = xml.count(old)
        if count != 1:
            raise ValueError(
                "anchor not unique (count=%d): %r" % (count, old))
        xml = xml.replace(old, new)
        results.append({"old": old, "new": new, "delta": len(new) - len(old)})
    return xml, results


_IMGDIM_TAG = re.compile(r'<hp:imgDim\b[^>]*>')
_DIMWIDTH = re.compile(r'dimwidth="(\d+)"')
_DIMHEIGHT = re.compile(r'dimheight="(\d+)"')


def png_dimensions(data):
    # PNG signature (8) + length(4) + "IHDR"(4) then width(4), height(4)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def img_dims(xml):
    out = []
    for tag in _IMGDIM_TAG.findall(xml):
        w = _DIMWIDTH.search(tag)
        h = _DIMHEIGHT.search(tag)
        if w and h:
            out.append((int(w.group(1)), int(h.group(1))))
    return out


def clone_equation(xml, template_script, anchor):
    m = re.search(
        r'<hp:equation\b[^>]*>(?:(?!</hp:equation>).)*?<hp:script>'
        + re.escape(template_script)
        + r'</hp:script>.*?</hp:equation>', xml, re.S)
    if not m:
        raise ValueError("template equation not found: %r" % template_script)
    if xml.count(anchor) != 1:
        raise ValueError("anchor not unique: %r" % anchor)
    existing = [int(i) for i in _EQ_ID.findall(xml)]
    new_id = (max(existing) + 1) if existing else 1
    clone = re.sub(r'(<hp:equation\s+id=")\d+(")',
                   r'\g<1>%d\g<2>' % new_id, m.group(0), count=1)
    return xml.replace(anchor, clone + anchor, 1)


def _memo_spans(xml):
    return [(m.start(), m.end()) for m in _MEMO_SUBLIST.finditer(xml)]


def _mask_memos(xml):
    spans = _memo_spans(xml)
    if not spans:
        return xml
    chars = list(xml)
    for s, e in spans:
        for i in range(s, e):
            chars[i] = "#"
    return "".join(chars)


def enumerate_body_paragraphs(xml, eq_marker="⟨식⟩"):
    masked = _mask_memos(xml)
    mspans = _memo_spans(xml)
    out = []
    idx = -1
    for pm in _P.finditer(masked):
        s, e = pm.start(), pm.end()
        region = xml[s:e]
        body = strip_memo_sublists(region)
        body = _EQUATION.sub(f"<hp:t>{eq_marker}</hp:t>", body)
        display = "".join(_T.findall(body)).strip()
        if not display:
            continue
        idx += 1
        t_nodes = []
        for tm in _T.finditer(region):
            a = s + tm.start(1)
            b = s + tm.end(1)
            if not any(ms <= a < me for ms, me in mspans):
                t_nodes.append((a, b))
        out.append({"index": idx, "display": display, "t_nodes": t_nodes})
    return out
