# hwpx-toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Claude Code + Codex plugin repo that safely reads and edits 한글(HWPX) files, packaging the session-developed workflows (memo removal, char-delta text edits, figure swap, equation clone) as one skill with a unified `hwpx.py` CLI.

**Architecture:** A single shared skill (`skills/hwpx-edit/`) holds a stdlib-only Python library (`_hwpxlib.py`) plus a CLI dispatcher (`hwpx.py`). Deterministic/verifiable operations live in scripts; language judgment stays with the model (guided by `SKILL.md`). Claude Code and Codex both load the same `SKILL.md`; platform differences are install manifests only.

**Tech Stack:** Python 3.9+ (stdlib only: `zipfile`, `re`, `xml.dom.minidom`, `argparse`, `struct`, `collections`), pytest for tests. No third-party runtime dependencies.

## Global Constraints

- **Python 3.9+, standard library only** for `_hwpxlib.py` and `hwpx.py` (runtime has no third-party deps). pytest is a test-only dependency.
- **Never modify input in place** — every write command takes `-o <out>` and produces a new file.
- **Repackage by structure-clone**: preserve the original zip infolist order and each entry's `compress_type` (mimetype stays first + STORED); add zero directory entries. Never shell out to `zip`.
- **Strip ALL `<hp:linesegarray>`** whenever section XML text changes.
- **Verify well-formed** (`xml.dom.minidom.parseString`) before writing.
- **`edit` anchors must be unique** (count == 1) or the command errors without writing.
- **Char deltas count Unicode codepoints** (`len(str)`), spaces included.
- **License: MIT.** Repo name `hwpx-toolkit`, skill name `hwpx-edit`.
- Section content path inside HWPX: `Contents/section0.xml`. Memo fields are `<hp:fieldBegin ... type="MEMO" ...>`; hyperlink fields are `type="HYPERLINK"` and must be preserved.

---

### Task 1: Repo scaffolding + test fixture builder

**Files:**
- Create: `skills/hwpx-edit/scripts/_hwpxlib.py` (empty module + version constant)
- Create: `tests/conftest.py`
- Create: `tests/test_fixture.py`
- Create: `pytest.ini`
- Create: `.gitignore`

**Interfaces:**
- Produces: `tests/conftest.py::SECTION_XML` (str, a representative `section0.xml`), `make_hwpx(dir_path, section_xml=SECTION_XML) -> str` (writes a minimal valid `.hwpx`, returns its path), and a pytest fixture `sample_hwpx(tmp_path) -> str`.

- [ ] **Step 1: Write the fixture builder and a test that opens it**

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
```

Create `.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
```

Create `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
"""hwpx-toolkit core library (stdlib only)."""
__version__ = "0.1.0"
```

Create `tests/conftest.py`:
```python
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
```

Create `tests/test_fixture.py`:
```python
import zipfile

from conftest import make_hwpx


def test_fixture_opens_and_mimetype_first_stored(sample_hwpx):
    with zipfile.ZipFile(sample_hwpx) as z:
        infos = z.infolist()
        assert infos[0].filename == "mimetype"
        assert infos[0].compress_type == zipfile.ZIP_STORED
        assert z.read("mimetype") == b"application/hwp+zip"
        assert "Contents/section0.xml" in z.namelist()
```

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_fixture.py -v`
Expected: PASS (2 assertions in one test).

Note: `conftest.py` in `tests/` is auto-imported by pytest; `from conftest import make_hwpx` works because pytest adds the test dir to `sys.path` (rootdir insertion). If import fails, add `tests/__init__.py` is NOT wanted; instead rely on pytest rootdir. Confirm by running the command above.

- [ ] **Step 3: Commit**

```bash
git add pytest.ini .gitignore skills/hwpx-edit/scripts/_hwpxlib.py tests/conftest.py tests/test_fixture.py
git commit -m "test: minimal HWPX fixture builder + scaffolding"
```

---

### Task 2: Read/extract functions in `_hwpxlib`

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py`
- Create: `tests/test_extract.py`

**Interfaces:**
- Produces:
  - `read_section(hwpx_path) -> str` — return `Contents/section0.xml` text.
  - `strip_memo_sublists(xml) -> str` — remove memo comment subLists only (for body reading).
  - `plain_text(xml, eq_marker="⟨식⟩") -> str` — concatenated `<hp:t>` text with memo comments removed and equations replaced by `eq_marker`.
  - `paragraph_texts(xml, eq_marker="⟨식⟩") -> list[str]` — one plain-text string per `<hp:p>` (memo comments removed, equations marked), empty paragraphs omitted.
  - `list_equations(xml) -> collections.Counter` — map equation `<hp:script>` text → count.

- [ ] **Step 1: Write failing tests**

Create `tests/test_extract.py`:
```python
import _hwpxlib as lib
from conftest import SECTION_XML


def test_read_section(sample_hwpx):
    xml = lib.read_section(sample_hwpx)
    assert "Contents" not in xml  # it's the section content, not a path
    assert "<hp:t>첫 문단 본문이다.</hp:t>" in xml


def test_plain_text_drops_memo_comment_marks_equation():
    txt = lib.plain_text(SECTION_XML)
    assert "이건 메모 주석이다" not in txt      # memo comment removed
    assert "앵커 본문" in txt                    # anchored body kept
    assert "링크텍스트" in txt                   # hyperlink text kept
    assert "⟨식⟩" in txt                         # equation marked
    assert "device _{key}" not in txt            # raw script not in body


def test_paragraph_texts():
    paras = lib.paragraph_texts(SECTION_XML)
    assert paras[0] == "첫 문단 본문이다."
    assert paras[1].startswith("앵커 본문을 이어서 쓴다. 링크텍스트⟨식⟩로 끝난다.")


def test_list_equations():
    eqs = lib.list_equations(SECTION_XML)
    assert eqs["device _{key}"] == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_extract.py -v`
Expected: FAIL (`AttributeError: module '_hwpxlib' has no attribute 'read_section'`).

Note: tests import `_hwpxlib`; add its dir to path. Put this at top of `tests/conftest.py` (prepend, before other imports):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "hwpx-edit" / "scripts"))
```
(Insert this block; re-run to confirm the failure is now "no attribute", not "no module".)

- [ ] **Step 3: Implement extract functions**

Append to `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
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
    body = _EQUATION.sub(eq_marker, body)
    return "".join(_T.findall(body))


def paragraph_texts(xml, eq_marker="⟨식⟩"):
    body = strip_memo_sublists(xml)
    body = _EQUATION.sub(eq_marker, body)
    out = []
    for p in _P.findall(body):
        t = "".join(_T.findall(p)).strip()
        if t:
            out.append(t)
    return out


def list_equations(xml):
    return collections.Counter(_SCRIPT.findall(xml))
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_extract.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/conftest.py tests/test_extract.py
git commit -m "feat: HWPX read/extract (section, plain_text, paragraphs, equations)"
```

---

### Task 3: Safety core — repackage, strip_linesegarray, well-formed, verify

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py`
- Create: `tests/test_safety.py`

**Interfaces:**
- Produces:
  - `repackage(original_path, out_path, replacements: dict[str, bytes]) -> None` — clone zip structure, swap named arcnames.
  - `strip_linesegarray(xml) -> str` — remove all `<hp:linesegarray>...</hp:linesegarray>` and self-closing forms.
  - `is_wellformed(xml) -> bool` — True if `xml.dom.minidom.parseString` succeeds, else raises `ValueError`.
  - `verify(hwpx_path) -> dict` — keys: `wellformed` (bool), `linesegarray` (int), `memo_fields` (int), `hyperlink_fields` (int), `dup_equation_ids` (list[str]).

- [ ] **Step 1: Write failing tests**

Create `tests/test_safety.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_safety.py -v`
Expected: FAIL (`AttributeError` for `strip_linesegarray`).

- [ ] **Step 3: Implement safety functions**

Append to `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_safety.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_safety.py
git commit -m "feat: safety core (repackage, strip_linesegarray, is_wellformed, verify)"
```

---

### Task 4: Memo list + remove

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py`
- Create: `tests/test_memo.py`

**Interfaces:**
- Produces:
  - `list_memos(xml) -> list[dict]` — each dict: `id` (str), `author` (str|None), `comment` (str).
  - `remove_memos(xml) -> tuple[str, int]` — remove all MEMO `<hp:ctrl>`-wrapped fieldBegin+fieldEnd, keep anchored text and HYPERLINK fields; return (new_xml, removed_count).

- [ ] **Step 1: Write failing tests**

Create `tests/test_memo.py`:
```python
import _hwpxlib as lib
from conftest import SECTION_XML


def test_list_memos():
    memos = lib.list_memos(SECTION_XML)
    assert len(memos) == 1
    assert memos[0]["id"] == "memo1"
    assert memos[0]["comment"] == "이건 메모 주석이다"


def test_remove_memos_keeps_body_and_hyperlink():
    out, n = lib.remove_memos(SECTION_XML)
    assert n == 1
    assert 'type="MEMO"' not in out
    assert "이건 메모 주석이다" not in out       # comment gone
    assert "앵커 본문" in out                     # anchored body kept
    assert 'type="HYPERLINK"' in out              # hyperlink preserved
    assert "링크텍스트" in out
    assert lib.is_wellformed(out) is True
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_memo.py -v`
Expected: FAIL (`AttributeError: list_memos`).

- [ ] **Step 3: Implement memo functions**

Append to `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
_MEMO_FIELD = re.compile(
    r'<hp:ctrl><hp:fieldBegin[^>]*type="MEMO".*?</hp:fieldBegin></hp:ctrl>', re.S)
_MEMO_ID = re.compile(
    r'<hp:fieldBegin id="(\d+)" type="MEMO"')
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
    memo_ids = _MEMO_ID.findall(xml)
    new_xml, n = _MEMO_FIELD.subn("", xml)
    for mid in memo_ids:
        pat = r'<hp:ctrl><hp:fieldEnd beginIDRef="%s"[^>]*/></hp:ctrl>' % re.escape(mid)
        new_xml = re.sub(pat, "", new_xml)
    return new_xml, n
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_memo.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_memo.py
git commit -m "feat: memo list + remove (preserve anchors and hyperlinks)"
```

---

### Task 5: Char-delta text edits (`apply_replacements`)

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py`
- Create: `tests/test_edit.py`

**Interfaces:**
- Produces:
  - `apply_replacements(xml, pairs) -> tuple[str, list[dict]]` where `pairs` is `list[(old, new)]`. For each pair: assert `xml.count(old) == 1` else raise `ValueError` naming the count and old; apply; record `{"old": old, "new": new, "delta": len(new) - len(old)}`. Returns (new_xml, results).

- [ ] **Step 1: Write failing tests**

Create `tests/test_edit.py`:
```python
import pytest

import _hwpxlib as lib
from conftest import SECTION_XML


def test_apply_replacements_unique_and_delta():
    out, res = lib.apply_replacements(
        SECTION_XML, [("첫 문단 본문이다.", "첫 문단 본문이 조금 늘었다.")])
    assert "첫 문단 본문이 조금 늘었다." in out
    assert res[0]["delta"] == len("첫 문단 본문이 조금 늘었다.") - len("첫 문단 본문이다.")


def test_apply_replacements_rejects_non_unique():
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [("<hp:t>", "<hp:t>")])  # appears many times


def test_apply_replacements_rejects_absent():
    with pytest.raises(ValueError):
        lib.apply_replacements(SECTION_XML, [("존재하지않는문자열", "x")])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_edit.py -v`
Expected: FAIL (`AttributeError: apply_replacements`).

- [ ] **Step 3: Implement**

Append to `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_edit.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_edit.py
git commit -m "feat: char-delta text edits with anchor uniqueness"
```

---

### Task 6: Figure swap + equation clone

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py`
- Create: `tests/test_figure_eqn.py`

**Interfaces:**
- Produces:
  - `png_dimensions(data: bytes) -> tuple[int, int]` — width, height from PNG IHDR.
  - `img_dims(xml) -> list[tuple[int, int]]` — `(dimwidth, dimheight)` from each `<hp:imgDim>` (HWPUNIT).
  - `clone_equation(xml, template_script, anchor) -> str` — copy an existing `<hp:equation>` whose `<hp:script>` equals `template_script`, assign a fresh id (max existing id + 1), and insert it immediately before `anchor` (which must be unique). Returns new_xml. Raises `ValueError` if template not found or anchor not unique.

- [ ] **Step 1: Write failing tests**

Create `tests/test_figure_eqn.py`:
```python
import pytest

import _hwpxlib as lib
from conftest import SECTION_XML, PNG_1x1


def test_png_dimensions():
    assert lib.png_dimensions(PNG_1x1) == (1, 1)


def test_clone_equation_fresh_id():
    out = lib.clone_equation(SECTION_XML, "device _{key}", "로 끝난다.")
    ids = lib._EQ_ID.findall(out)
    assert len(ids) == 2                 # original + clone
    assert len(set(ids)) == 2            # ids are unique
    assert lib.is_wellformed(out) is True


def test_clone_equation_bad_template():
    with pytest.raises(ValueError):
        lib.clone_equation(SECTION_XML, "no such script", "로 끝난다.")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_figure_eqn.py -v`
Expected: FAIL (`AttributeError: png_dimensions`).

- [ ] **Step 3: Implement**

Append to `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
import struct

_IMGDIM = re.compile(r'<hp:imgDim\s+dimwidth="(\d+)"\s+dimheight="(\d+)"')


def png_dimensions(data):
    # PNG signature (8) + length(4) + "IHDR"(4) then width(4), height(4)
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def img_dims(xml):
    return [(int(w), int(h)) for w, h in _IMGDIM.findall(xml)]


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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_figure_eqn.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_figure_eqn.py
git commit -m "feat: png dimensions, img_dims, equation clone"
```

---

### Task 7: CLI dispatcher `hwpx.py` + end-to-end tests

**Files:**
- Create: `skills/hwpx-edit/scripts/hwpx.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: all `_hwpxlib` functions above.
- Produces: a CLI with subcommands `extract`, `memo clear`, `edit`, `figure swap`, `equation clone`, `verify`, `repackage`. Each write command applies the safety pipeline: read section → transform → `strip_linesegarray` (for text/memo changes) → `is_wellformed` → `repackage` to `-o`.

- [ ] **Step 1: Write failing end-to-end tests**

Create `tests/test_cli.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL (CLI file missing → non-zero returncode / traceback).

- [ ] **Step 3: Implement the CLI**

Create `skills/hwpx-edit/scripts/hwpx.py`:
```python
#!/usr/bin/env python3
"""hwpx-toolkit CLI. Safe read/edit of 한글(HWPX) files.

All write subcommands: never modify input in place; strip linesegarray on
text changes; verify well-formed; repackage via structure-clone.
"""
import argparse
import sys

import _hwpxlib as lib


def _write(original, out, new_section):
    lib.is_wellformed(new_section)
    lib.repackage(original, out,
                  {lib.SECTION_PATH: new_section.encode("utf-8")})


def cmd_extract(a):
    xml = lib.read_section(a.file)
    if a.paragraphs:
        for i, p in enumerate(lib.paragraph_texts(xml)):
            print("[%d] %s" % (i, p))
    elif a.memos:
        for m in lib.list_memos(xml):
            print("%s\t%s\t%s" % (m["id"], m["author"], m["comment"]))
    elif a.equations:
        for script, n in lib.list_equations(xml).most_common():
            print("%3d  %s" % (n, script))
    else:
        print(lib.plain_text(xml))
    return 0


def cmd_memo_clear(a):
    xml = lib.read_section(a.file)
    new_xml, n = lib.remove_memos(xml)
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("removed %d memo(s) -> %s" % (n, a.out))
    return 0


def _parse_replace(items):
    pairs = []
    for it in items:
        if "\t" not in it:
            raise SystemExit("--replace needs old<TAB>new: %r" % it)
        old, new = it.split("\t", 1)
        pairs.append((old, new))
    return pairs


def cmd_edit(a):
    xml = lib.read_section(a.file)
    pairs = _parse_replace(a.replace)
    try:
        new_xml, results = lib.apply_replacements(xml, pairs)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for r in results:
        print("delta %+d  %r -> %r" % (r["delta"], r["old"][:30], r["new"][:30]))
    if a.check:
        print("(--check: no file written)")
        return 0
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("wrote %s" % a.out)
    return 0


def cmd_figure_swap(a):
    with open(a.png, "rb") as f:
        png = f.read()
    xml = lib.read_section(a.file)
    dims = lib.img_dims(xml)
    pw, ph = lib.png_dimensions(png)
    print("new PNG %dx%d (aspect %.3f)" % (pw, ph, pw / ph))
    for w, h in dims:
        print("  imgDim %dx%d (aspect %.3f)" % (w, h, w / h))
    arc = "BinData/%s.png" % a.slot
    lib.repackage(a.file, a.out, {arc: png})
    print("swapped %s -> %s" % (arc, a.out))
    return 0


def cmd_equation_clone(a):
    xml = lib.read_section(a.file)
    new_xml = lib.clone_equation(xml, a.template, a.anchor)
    new_xml = lib.strip_linesegarray(new_xml)
    _write(a.file, a.out, new_xml)
    print("cloned equation -> %s" % a.out)
    return 0


def cmd_verify(a):
    print(lib.verify(a.file))
    return 0


def cmd_repackage(a):
    reps = {}
    for it in a.replace:
        arc, path = it.split("=", 1)
        with open(path, "rb") as f:
            reps[arc] = f.read()
    lib.repackage(a.original, a.out, reps)
    print("repackaged -> %s" % a.out)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="hwpx")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract")
    e.add_argument("file")
    g = e.add_mutually_exclusive_group()
    g.add_argument("--paragraphs", action="store_true")
    g.add_argument("--memos", action="store_true")
    g.add_argument("--equations", action="store_true")
    e.set_defaults(func=cmd_extract)

    m = sub.add_parser("memo")
    msub = m.add_subparsers(dest="mcmd", required=True)
    mc = msub.add_parser("clear")
    mc.add_argument("file")
    mc.add_argument("-o", "--out", required=True)
    mc.set_defaults(func=cmd_memo_clear)

    ed = sub.add_parser("edit")
    ed.add_argument("file")
    ed.add_argument("-o", "--out", required=True)
    ed.add_argument("--replace", action="append", default=[],
                    help="old<TAB>new (repeatable)")
    ed.add_argument("--check", action="store_true")
    ed.set_defaults(func=cmd_edit)

    fg = sub.add_parser("figure")
    fsub = fg.add_subparsers(dest="fcmd", required=True)
    fs = fsub.add_parser("swap")
    fs.add_argument("file")
    fs.add_argument("-o", "--out", required=True)
    fs.add_argument("--slot", required=True, help="e.g. image2")
    fs.add_argument("--png", required=True)
    fs.set_defaults(func=cmd_figure_swap)

    eq = sub.add_parser("equation")
    esub = eq.add_subparsers(dest="ecmd", required=True)
    ec = esub.add_parser("clone")
    ec.add_argument("file")
    ec.add_argument("-o", "--out", required=True)
    ec.add_argument("--template", required=True)
    ec.add_argument("--anchor", required=True)
    ec.set_defaults(func=cmd_equation_clone)

    v = sub.add_parser("verify")
    v.add_argument("file")
    v.set_defaults(func=cmd_verify)

    rp = sub.add_parser("repackage")
    rp.add_argument("--original", required=True)
    rp.add_argument("-o", "--out", required=True)
    rp.add_argument("--replace", action="append", default=[],
                    help="arcname=path (repeatable)")
    rp.set_defaults(func=cmd_repackage)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (5 tests). Then run the full suite: `python -m pytest -v` → all green.

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/hwpx.py tests/test_cli.py
git commit -m "feat: unified hwpx CLI (extract/memo/edit/figure/equation/verify/repackage)"
```

---

### Task 8: Skill docs, references, packaging manifests, README

**Files:**
- Create: `skills/hwpx-edit/SKILL.md`
- Create: `skills/hwpx-edit/references/hwpx-internals.md` (port from `~/.claude/skills/hwpx-edit/references/hwpx-internals.md`)
- Create: `skills/hwpx-edit/references/workflows.md`
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `codex/install.md`
- Create: `README.md`
- Create: `LICENSE`

**Interfaces:**
- Produces: installable plugin metadata + the model-facing workflow guidance that ties CLI commands to the safety rules.

- [ ] **Step 1: Write `plugin.json` and validate JSON**

Create `.claude-plugin/plugin.json`:
```json
{
  "name": "hwpx-edit",
  "version": "0.1.0",
  "description": "Safely read and edit 한글(HWPX) files: memo removal, char-delta text edits, figure swap, equation clone — via a structure-preserving CLI.",
  "author": { "name": "KimJongGun" }
}
```

Create `.claude-plugin/marketplace.json`:
```json
{
  "name": "hwpx-toolkit",
  "owner": { "name": "KimJongGun" },
  "plugins": [
    { "name": "hwpx-edit", "source": "./", "description": "HWPX read/edit skill + CLI" }
  ]
}
```

Validate: `python -c "import json; json.load(open('.claude-plugin/plugin.json')); json.load(open('.claude-plugin/marketplace.json')); print('ok')"`
Expected: `ok`

- [ ] **Step 2: Write `LICENSE` (MIT)**

Create `LICENSE` with the standard MIT text, year 2026, copyright holder `KimJongGun`.

- [ ] **Step 3: Port `hwpx-internals.md` and write `workflows.md` + `SKILL.md`**

Copy the internals reference:
```bash
cp ~/.claude/skills/hwpx-edit/references/hwpx-internals.md skills/hwpx-edit/references/hwpx-internals.md
```

Create `skills/hwpx-edit/references/workflows.md` documenting, with concrete `hwpx.py` command examples, the recipes: **widow ±N char adjustment** (use `extract --paragraphs` to read, craft meaning-preserving unique-anchor replacements, `edit --check` to confirm deltas, then `edit`), **memo clear**, **figure swap** (aspect match), **equation subscript restore** (`equation clone`), and **citation/reference notes** (plain-text edits via `edit`). Each recipe names the safety rule it relies on.

Create `skills/hwpx-edit/SKILL.md`:
```markdown
---
name: hwpx-edit
description: Use for ANY task that edits an existing .hwpx (한글) file and saves it back as .hwpx — the safe way to modify .hwpx without corrupting it. Covers reading body/memo/equation text, removing memos, adjusting paragraph length by exact character count, swapping embedded figures, and restoring subscript equations. Do NOT use for PDF/format conversion or authoring a new document.
---

# Editing HWPX safely

HWPX is a ZIP of OWPML XML. Two traps: HWP refuses to open a carelessly rebuilt
zip, and stale line caches make text overlap. This skill's CLI handles both.

## The CLI
Run: `python3 <this skill>/scripts/hwpx.py <subcommand>`
(On Claude Code the skill dir is `${CLAUDE_PLUGIN_ROOT}/skills/hwpx-edit`.)

- `extract FILE [--paragraphs|--memos|--equations]` — read content.
- `memo clear FILE -o OUT` — remove all memos, keep body + hyperlinks.
- `edit FILE -o OUT --replace "old<TAB>new" [...] [--check]` — unique-anchor
  replacements; prints each char delta. Use `--check` first.
- `figure swap FILE -o OUT --slot imageN --png P` — replace embedded PNG.
- `equation clone FILE -o OUT --template "device _{key}" --anchor "PLAIN"` —
  restore a subscript term as an equation object.
- `verify FILE` — structural gate.

## Non-negotiable rules
1. Never edit the original in place — always `-o` a new version (bump the ver number).
2. The CLI repackages by structure-clone; never shell `zip`.
3. Text changes strip all linesegarray (CLI does this) so HWP recomputes layout.
4. `edit` anchors MUST be unique. Choose anchors in **pure Korean** runs — never
   spanning an `<hp:equation>` or containing `&gt;` (the XML escape for `>`).
5. You (the model) craft the replacement text: meaning-preserving, hitting the
   requested character delta; the CLI reports the delta so you can check.

## Limitation
The environment cannot render HWPX. After editing, tell the author to open the
file in HWP and eyeball layout (a benign "변조 가능성" warning may appear).
See references/hwpx-internals.md and references/workflows.md.
```

- [ ] **Step 4: Write `codex/install.md` and `README.md`**

Create `codex/install.md` explaining: clone the repo, then make the skill visible to Codex by copying or symlinking `skills/hwpx-edit/` into the Codex skills directory (`~/.codex/skills/hwpx-edit` or a project `.codex/skills/`), and that the CLI is invoked as `python3 <skill>/scripts/hwpx.py`.

Create `README.md` covering: what it is, the safety guarantees, install for Claude Code (`/plugin marketplace add <owner>/hwpx-toolkit` → `/plugin install hwpx-edit`), install for Codex (see `codex/install.md`), a usage example (memo clear + a widow `edit --check`), and `python -m pytest` for contributors.

- [ ] **Step 5: Run full suite + JSON validation, then commit**

Run: `python -m pytest -v` (all green) and the JSON validation from Step 1.
```bash
git add SKILL LICENSE README.md .claude-plugin codex skills/hwpx-edit/SKILL.md skills/hwpx-edit/references
git add -A
git commit -m "docs: SKILL.md, references, README, MIT license, plugin manifests"
```

---

## Self-Review

**Spec coverage:**
- §3 repo structure → Tasks 1,7,8 create all listed files (LICENSE, README, .claude-plugin/*, skills/hwpx-edit/{SKILL.md,scripts/*,references/*}, codex/install.md, tests/*). ✓
- §4 CLI subcommands extract/memo/edit/figure/equation/verify/repackage → Tasks 2–7 (lib) + Task 7 (CLI). ✓
- §5 script/model split → encoded in SKILL.md (Task 8) + lib determinism (Tasks 2–6). ✓
- §6 safety invariants → repackage/strip/wellformed/uniqueness (Tasks 3,5) + `_write` pipeline (Task 7) + SKILL rules (Task 8). ✓
- §7 packaging (both platforms) → Task 8 (plugin.json, marketplace.json, codex/install.md). ✓
- §8 tests → Tasks 1–7 each add pytest coverage for their deliverable. ✓
- §9 naming/license/README → Task 8. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; test code is concrete. Task 8 Steps 3–4 describe prose docs (SKILL.md shown in full; workflows.md/README/codex described by required contents) — acceptable since those are documentation deliverables, not code.

**Type consistency:** `SECTION_PATH`, `read_section`, `plain_text`, `paragraph_texts`, `list_equations`, `strip_linesegarray`, `is_wellformed`, `repackage`, `verify`, `list_memos`, `remove_memos`, `apply_replacements`, `png_dimensions`, `img_dims`, `clone_equation`, `_EQ_ID` — names used in `hwpx.py` (Task 7) and tests match their definitions in Tasks 2–6. ✓

**Note for implementer:** `_EQ_ID`/`_T` are module-level regexes reused across functions and by a test (`lib._EQ_ID`); keep them defined once at first use (Task 3 defines `_EQ_ID`, Task 2 defines `_T`). If running tasks out of order, ensure earlier-numbered definitions exist before later references.
