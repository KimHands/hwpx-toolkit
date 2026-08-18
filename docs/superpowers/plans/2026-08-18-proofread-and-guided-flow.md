# proofread + 가이드 작업 선택 플로우 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 hwpx-toolkit에 문단 스코프 맞춤법 교정(`proofread apply`)과 스킬 레벨 가이드 작업 선택 플로우를 손상 없이 추가한다.

**Architecture:** 검사(언어 판단)는 모델이 하고, 반영(결정론)은 스크립트가 한다. 교정은 본문 `<hp:t>` 노드의 **원문(raw) 텍스트**에서만 매칭·치환하며(언이스케이프 안 함), **매칭된 스팬만 splice**하고 삽입되는 `new`만 `xml.sax.saxutils.escape`로 이스케이프해 나머지 엔티티를 바이트 그대로 보존한다. 문단 열거는 메모 스팬을 등길이 필러로 마스킹한 뒤 분할하여 기존 `paragraph_texts`와 동일하게 맞춘다. 가이드 플로우는 SKILL.md 문서로만 구현한다.

**Tech Stack:** Python 3.9+ (stdlib only: `re`, `json`, `xml.sax.saxutils`), pytest(테스트 전용, `.venv/bin/pytest`로 실행 — 시스템 파이썬은 PEP 668로 막힘).

## Global Constraints

- **Python 3.9+, 표준 라이브러리만**. 신규 런타임 서드파티 의존성 금지. **외부 발송/네트워크 없음**.
- **원본 in-place 수정 금지** — 모든 쓰기는 `-o` 새 파일.
- **텍스트 변경 시 `strip_linesegarray`**, **쓰기 전 `is_wellformed`**, **`repackage`는 구조 복제**(기존 `_write` 재사용).
- 교정 매칭·치환은 **본문 `<hp:t>` 원문 텍스트 좌표계**에서만. 메모 subList·태그·속성·수식 스크립트 제외.
- **언이스케이프하지 않는다.** 삽입되는 `new`만 `xml.sax.saxutils.escape`(=`& < >`). 매칭된 스팬 외 노드 내용은 바이트 보존.
- 문단 번호 = `extract --paragraphs`(=`paragraph_texts`) 열거와 동일.
- **기존 `paragraph_texts`는 변경 금지**(회귀 방지). 섹션 경로는 `Contents/section0.xml` 단일.
- 테스트 실행: `.venv/bin/pytest`. 전체 스위트는 현재 27개 → 이 계획 완료 시 증가.

---

### Task 1: 문단 열거 — `enumerate_body_paragraphs` + 메모 마스킹 헬퍼

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py` (상단 import에 `from xml.sax.saxutils import escape as _xml_escape` 추가; 파일 끝에 함수 추가)
- Create: `tests/test_proofread.py`

**Interfaces:**
- Consumes: 기존 `_MEMO_SUBLIST`, `_P`, `_T`, `_EQUATION`, `strip_memo_sublists`, `paragraph_texts`.
- Produces:
  - `_memo_spans(xml) -> list[tuple[int,int]]`
  - `_mask_memos(xml) -> str` (메모 구간을 같은 길이 `#`로 치환)
  - `enumerate_body_paragraphs(xml, eq_marker="⟨식⟩") -> list[dict]`, 각 원소 `{"index": int, "display": str, "t_nodes": list[tuple[int,int]]}` (`t_nodes` = 본문 `<hp:t>` **내부 텍스트**의 원본 절대 오프셋, 메모 제외). `display`는 `paragraph_texts`와 문자 그대로 일치.

- [ ] **Step 1: Write the failing test**

Create `tests/test_proofread.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_proofread.py -v`
Expected: FAIL (`AttributeError: module '_hwpxlib' has no attribute 'enumerate_body_paragraphs'`).

- [ ] **Step 3: Write minimal implementation**

Add to the top import block of `skills/hwpx-edit/scripts/_hwpxlib.py` (next to the other imports near the top):
```python
from xml.sax.saxutils import escape as _xml_escape
```

Append to the end of `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_proofread.py -v`
Expected: PASS (3 tests). Then run full suite `.venv/bin/pytest -q` — all green (30 total).

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_proofread.py
git commit -m "feat: enumerate_body_paragraphs (memo-masked, matches paragraph_texts)"
```

---

### Task 2: 교정 적용 — `apply_paragraph_corrections`

**Files:**
- Modify: `skills/hwpx-edit/scripts/_hwpxlib.py` (파일 끝에 함수 추가)
- Modify: `tests/test_proofread.py` (테스트 추가)

**Interfaces:**
- Consumes: `enumerate_body_paragraphs`, `_xml_escape`, `is_wellformed`.
- Produces: `apply_paragraph_corrections(xml, corrections) -> tuple[str, list[dict]]`.
  `corrections` 원소 = `{"p": int, "old": str, "new": str}`. 반환 results 원소 = `{"p","old","new","delta"}`(입력 순서). 검증 실패 시 `ValueError`(아무것도 쓰지 않음).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_proofread.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_proofread.py -v`
Expected: FAIL (`AttributeError: ... 'apply_paragraph_corrections'`).

- [ ] **Step 3: Write minimal implementation**

Append to the end of `skills/hwpx-edit/scripts/_hwpxlib.py`:
```python
def apply_paragraph_corrections(xml, corrections):
    if not corrections:
        raise ValueError("no corrections given")
    seen = set()
    for c in corrections:
        p, old, new = c["p"], c["old"], c["new"]
        if isinstance(p, bool) or not isinstance(p, int):
            raise ValueError("p must be an integer: %r" % (p,))
        if old == "":
            raise ValueError("old must be non-empty")
        if old == new:
            raise ValueError("old == new (no-op): %r" % (old,))
        key = (p, old, new)
        if key in seen:
            raise ValueError("duplicate correction: %r" % (key,))
        seen.add(key)

    paras = enumerate_body_paragraphs(xml)
    n = len(paras)
    plan = []      # (match_start, match_end, new)
    results = []   # input order
    for c in corrections:
        p, old, new = c["p"], c["old"], c["new"]
        if p < 0 or p >= n:
            raise ValueError(
                "paragraph index out of range: %d (have %d)" % (p, n))
        node = None
        total = 0
        for a, b in paras[p]["t_nodes"]:
            cnt = xml[a:b].count(old)
            total += cnt
            if cnt == 1 and node is None:
                node = (a, b)
        if total != 1 or node is None:
            raise ValueError(
                "anchor not unique in paragraph %d (count=%d): %r"
                % (p, total, old))
        a, b = node
        ms = a + xml[a:b].index(old)
        plan.append((ms, ms + len(old), new))
        results.append({"p": p, "old": old, "new": new,
                        "delta": len(new) - len(old)})

    order = sorted(range(len(plan)), key=lambda i: plan[i][0])
    for j in range(1, len(order)):
        if plan[order[j]][0] < plan[order[j - 1]][1]:
            raise ValueError("overlapping corrections in the same region")

    out = xml
    for ms, me, new in sorted(plan, key=lambda t: -t[0]):
        out = out[:ms] + _xml_escape(new) + out[me:]
    return out, results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_proofread.py -v`
Expected: PASS (all Task 1 + Task 2 tests). Full suite `.venv/bin/pytest -q` all green.

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/_hwpxlib.py tests/test_proofread.py
git commit -m "feat: apply_paragraph_corrections (span-splice, escape new, atomic)"
```

---

### Task 3: CLI `proofread apply` + E2E

**Files:**
- Modify: `skills/hwpx-edit/scripts/hwpx.py` (상단 `import json`; `cmd_proofread_apply` 추가; `build_parser`에 서브파서 등록)
- Modify: `tests/test_cli.py` (E2E 테스트 추가)

**Interfaces:**
- Consumes: `lib.read_section`, `lib.apply_paragraph_corrections`, `lib.strip_linesegarray`, `lib.is_wellformed`, 기존 `_write`.
- Produces: CLI `proofread apply FILE -o OUT --from corrections.json [--check]` (exit 2 on any input/matching error, no output file written).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_cli.py` (기존 `run`/`make_hwpx` 헬퍼 재사용):
```python
import json


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cli.py -k proofread -v`
Expected: FAIL (`invalid choice: 'proofread'` from argparse → non-zero, or no output file).

- [ ] **Step 3: Write minimal implementation**

Add near the top of `skills/hwpx-edit/scripts/hwpx.py` (with the other imports):
```python
import json
```

Add this handler after `cmd_edit` in `skills/hwpx-edit/scripts/hwpx.py`:
```python
def cmd_proofread_apply(a):
    xml = lib.read_section(a.file)
    try:
        with open(a.corrections, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("error: --from file not found: %s" % a.corrections,
              file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print("error: invalid JSON: %s" % exc, file=sys.stderr)
        return 2
    if not isinstance(data, list):
        print("error: corrections JSON must be an array", file=sys.stderr)
        return 2
    try:
        new_xml, results = lib.apply_paragraph_corrections(xml, data)
    except (ValueError, KeyError, TypeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for r in results:
        print("delta %+d  p%d  %r -> %r"
              % (r["delta"], r["p"], r["old"][:30], r["new"][:30]))
    new_xml = lib.strip_linesegarray(new_xml)
    lib.is_wellformed(new_xml)
    if a.check:
        print("(--check: no file written)")
        return 0
    _write(a.file, a.out, new_xml)
    print("wrote %s" % a.out)
    return 0
```

Register the subparser in `build_parser()` (add before `return p`):
```python
    pr = sub.add_parser("proofread")
    prsub = pr.add_subparsers(dest="pcmd", required=True)
    pa = prsub.add_parser("apply")
    pa.add_argument("file")
    pa.add_argument("-o", "--out", required=True)
    pa.add_argument("--from", dest="corrections", required=True,
                    help="path to JSON array of {p, old, new}")
    pa.add_argument("--check", action="store_true")
    pa.set_defaults(func=cmd_proofread_apply)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cli.py -k proofread -v`
Expected: PASS (4 tests). Then full suite `.venv/bin/pytest -q` — all green.

- [ ] **Step 5: Commit**

```bash
git add skills/hwpx-edit/scripts/hwpx.py tests/test_cli.py
git commit -m "feat: proofread apply CLI (paragraph-scoped, JSON corrections)"
```

---

### Task 4: 문서 — SKILL.md proofread + 가이드 플로우, workflows.md 레시피

**Files:**
- Modify: `skills/hwpx-edit/SKILL.md`
- Modify: `skills/hwpx-edit/references/workflows.md`

**Interfaces:**
- Consumes: 위 태스크가 만든 CLI 형태(`proofread apply FILE -o OUT --from corrections.json [--check]`).
- Produces: 모델용 가이드 문서(런타임 코드·테스트 없음).

- [ ] **Step 1: SKILL.md에 proofread 명령 + 가이드 플로우 절 추가**

`skills/hwpx-edit/SKILL.md`의 CLI 목록(`- \`verify FILE\`` 줄 뒤)에 추가:
```markdown
- `proofread apply FILE -o OUT --from corrections.json [--check]` — 문단 스코프
  맞춤법·문장 교정. corrections = `[{"p":문단번호,"old":"오타","new":"교정"}]`.
  `p`는 `extract --paragraphs`의 `[i]` 번호. `old`는 그 출력에 보인 **문자 그대로**
  (엔티티 `&gt;`·`&#8203;` 포함) 복사. `old`는 해당 문단 안에서 유일해야 하고 한
  `<hp:t>` 런 안에 있어야 한다(런 경계를 넘으면 안전 실패 → 더 짧은 단어 단위로 재시도).
  `--check`로 먼저 델타를 확인한 뒤 적용.
```

`skills/hwpx-edit/SKILL.md` 끝의 "## Limitation" 앞에 절 추가:
```markdown
## 가이드 플로우 (작업 선택)
여러 작업이 필요할 때, 한 흐름으로 진행한다:
1. **사전 스캔**: `verify FILE`(메모/하이퍼링크/수식 수) + 필요시
   `extract FILE --memos` / `--equations`로 무엇이 있는지 파악.
2. **작업 선택**: 아래 개념 작업 목록을 사용자에게 다중선택으로 제시하고 고르게 한다:
   확인(extract) · 메모 제거(memo clear) · 맞춤법·문장 교정(proofread) ·
   글자수 델타 편집(edit) · 그림 교체(figure swap) · 수식 복제/첨자 복원(equation clone) ·
   검증(verify).
3. **체이닝 실행**: 원본 → op1 `-o` v1 → op2 `-o` v2 → … → 최종. 번호 붙인 버전
   파일을 남긴다. **각 텍스트 변경 작업 직전, 직전 산출물에서 문단번호·앵커를 다시
   추출**한다(앞 작업이 문단 열거를 바꿨을 수 있음 — 원본 기준 번호를 재사용하지 말 것).
   `figure swap`은 바이너리 교체라 텍스트 안전 파이프라인 대상이 아니다.
4. **마무리**: 최종 파일에 `verify` 실행, 델타 요약을 보고하고, 저자에게 HWP로 열어
   레이아웃을 확인하라고 안내(양성 "변조 가능성" 경고가 나타날 수 있음).
5. 선택했지만 대상이 0건이면 그 단계는 건너뛰고 사용자에게 알린다.
```

- [ ] **Step 2: workflows.md에 레시피 추가**

`skills/hwpx-edit/references/workflows.md` 끝에 추가:
```markdown
## 맞춤법·문장 교정 (proofread)
의존 안전 규칙: 원본 in-place 금지 · 문단 내 유일 앵커 · new만 XML 이스케이프 · linesegarray strip · well-formed 검증.

1. 읽기: `python3 hwpx.py extract paper.hwpx --paragraphs`
   → `[0] …`, `[1] …` 번호별 문단.
2. 모델이 오류를 찾아 교정 JSON 작성(문단번호 `p`, 그 문단에 보인 그대로의 `old`, 교정 `new`):
   ```json
   [{"p": 3, "old": "됬다", "new": "됐다"},
    {"p": 7, "old": "할수있다", "new": "할 수 있다"}]
   ```
   corrections.json 으로 저장.
3. 미리보기: `python3 hwpx.py proofread apply paper.hwpx -o /tmp/preview.hwpx --from corrections.json --check`
   → 각 교정의 글자수 델타 출력, 파일은 안 씀.
4. 적용: `python3 hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json`
5. 검증: `python3 hwpx.py verify paper_v2.hwpx`
   `old`가 유일하지 않거나 런 경계를 넘으면 오류로 멈춘다 → 더 짧은 단어 단위 앵커로 재시도.

## 가이드 작업 선택 플로우
의존 안전 규칙: 각 텍스트 변경 작업 직전 직전 산출물에서 재추출(신선도) · 번호 버전 파일 유지 · 최종 verify.

1. 사전 스캔: `python3 hwpx.py verify doc.hwpx` (+ 필요시 `extract --memos`/`--equations`).
2. 사용자에게 작업 다중선택 제시 → 선택.
3. 선택 순서대로 체이닝: `memo clear doc.hwpx -o doc_v1.hwpx` →
   (재추출) `proofread apply doc_v1.hwpx -o doc_v2.hwpx --from c.json` → … .
4. 최종: `verify doc_vN.hwpx` 후 HWP로 열어 확인 안내.
```

- [ ] **Step 3: 문서 명령 형태 검증(수동)**

Run: `.venv/bin/pytest -q` (문서 변경이라 코드 회귀 없음 — 전체 그린 유지)
그리고 SKILL.md·workflows.md의 모든 `proofread`/`extract`/`verify`/`memo clear`/`figure swap` 예시가 실제 CLI 서브커맨드 형태와 일치하는지 눈으로 대조(Task 3의 argparse 정의 기준).

- [ ] **Step 4: Commit**

```bash
git add skills/hwpx-edit/SKILL.md skills/hwpx-edit/references/workflows.md
git commit -m "docs: proofread 명령 + 가이드 작업 선택 플로우 (SKILL.md, workflows.md)"
```

---

## Self-Review

**Spec coverage (rev3):**
- §A.1 좌표계(원문 매칭·스팬 splice·new만 escape) → Task 2 구현 + `test_apply_escapes_new`/`test_apply_preserves_untouched_entities`. ✓
- §A.3 `enumerate_body_paragraphs`(메모 마스킹·`_MEMO_SUBLIST`·문서순서 마커·t_nodes) → Task 1. ✓
- §A.3 `apply_paragraph_corrections`(입력검증·계획·겹침·내림차순 splice·원자성) → Task 2. ✓
- §A.4 CLI(`--from` JSON·`--check` is_wellformed·exit 2·출력미생성·`_write` 재사용) → Task 3. ✓
- §A.5 열거·좌표 동치(픽스처 + 엔티티 픽스처) → Task 1 `test_enumerate_matches_*`, `test_t_nodes_point_at_real_body_text`. ✓
- §A.6 한계(런 경계 안전 실패) → Task 2 `test_apply_run_boundary_anchor_fails_safely` + SKILL.md 안내(Task 4). ✓
- §B 가이드 플로우(사전스캔·체크리스트·신선도 재추출·figure swap 예외·no-op) → Task 4 SKILL.md/workflows.md. ✓
- §C 테스트 목록 → Task 1–3 각 테스트로 대응. ✓
- §D 비목표 → 신규 명령은 proofread apply 하나, TUI/외부API/정규화 없음. ✓

**Placeholder scan:** 모든 코드 단계에 완전한 코드. TBD/TODO 없음. Task 4는 문서 산출물(전문 제시). ✓

**Type consistency:** `enumerate_body_paragraphs`(dict: index/display/t_nodes), `apply_paragraph_corrections`(→ (str, list[dict] p/old/new/delta)), CLI `a.corrections`(dest of `--from`), `_xml_escape`, `import json` — Task 1→2→3 사용 이름·시그니처 일치. `_write`/`strip_linesegarray`/`is_wellformed`/`read_section` 기존 정의와 일치. ✓
