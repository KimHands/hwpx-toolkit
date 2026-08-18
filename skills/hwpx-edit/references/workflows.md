# hwpx-edit — Workflow recipes

These recipes show exact `hwpx.py` command sequences for the most common editing tasks. Each recipe names the safety rule(s) it relies on.

---

## 1. Widow ±N char adjustment

A "widow" is a short orphaned line at the top of a column or page. The fix is to shorten or lengthen the preceding paragraph by a small number of characters so the line breaks shift.

**Safety rules:** unique anchor, strip linesegarray (automatic), always write to `-o` new file.

**Procedure:**

```bash
# Step 1: read paragraphs to pick a unique anchor and plan the replacement
python3 skills/hwpx-edit/scripts/hwpx.py extract input.hwpx --paragraphs

# Step 2: dry-run to see the exact char delta (use TAB between old and new)
python3 skills/hwpx-edit/scripts/hwpx.py edit input.hwpx -o /dev/null \
  --replace "앞 문장의 특유한 구절	앞 문장의 조금 짧은 구절" --check

# Step 3: apply when the delta is what you want
python3 skills/hwpx-edit/scripts/hwpx.py edit input.hwpx -o output_v2.hwpx \
  --replace "앞 문장의 특유한 구절	앞 문장의 조금 짧은 구절"
```

Notes:
- The anchor must appear **exactly once** in the section XML — the CLI enforces this.
- Do NOT anchor across an `<hp:equation>` object or a `&gt;` escape sequence.
- After writing, tell the author to open the new file in HWP and check layout visually; a "변조 가능성" warning is benign.

---

## 2. Memo clear

Remove all reviewer memos (comments) while keeping body text and hyperlinks intact.

**Safety rule:** never edit original in place — output to new file.

```bash
python3 skills/hwpx-edit/scripts/hwpx.py memo clear input.hwpx -o output_nomemo.hwpx
```

Verify the result is well-formed:

```bash
python3 skills/hwpx-edit/scripts/hwpx.py verify output_nomemo.hwpx
```

---

## 3. Figure swap (aspect match)

Replace an embedded PNG (`imageN` slot) with a new PNG. Ensure the replacement PNG has the same or compatible aspect ratio to avoid distorted layout.

**Safety rules:** never edit original in place; repackage by structure-clone (STORED entry, mimetype first — CLI handles this, never shell `zip`).

```bash
# Inspect which figure slots exist
python3 skills/hwpx-edit/scripts/hwpx.py extract input.hwpx

# Swap image3.png with new_figure.png
python3 skills/hwpx-edit/scripts/hwpx.py figure swap input.hwpx \
  -o output_fig.hwpx --slot image3 --png new_figure.png
```

The CLI checks that the replacement PNG is readable and warns if dimensions differ significantly from the original. Confirm aspect ratio before running.

---

## 4. Equation subscript restore (equation clone)

A subscripted term like `device_{key}` is an `<hp:equation>` object — not plain text. If one was accidentally deleted or needs to be inserted in a new location, clone an existing equation object and give it a fresh ID.

**Safety rule:** equation IDs must be unique; the CLI assigns a new ID automatically.

```bash
# Find available equation templates in the document
python3 skills/hwpx-edit/scripts/hwpx.py extract input.hwpx --equations

# Clone the equation matching "device _{key}" and insert it after the anchor text
python3 skills/hwpx-edit/scripts/hwpx.py equation clone input.hwpx \
  -o output_eq.hwpx \
  --template "device _{key}" \
  --anchor "앵커로 쓸 주변 순수 한국어 텍스트"
```

Notes:
- `--template` uses HancomEQN script syntax: `_{sub}` for subscript, `^{sup}` for superscript.
- `--anchor` must be plain Korean text, not a run containing an equation or `&gt;`.
- Do NOT try to author a brand-new multi-subscript display equation by hand; prefer prose unless the author insists.

---

## 5. Citation / reference edits (plain-text via edit)

In-text citations (`[1]`, `[4],[5]`) and reference-list entries are plain `<hp:t>` text. Renumber or update them with `edit`, using temp tokens to avoid cascade replacement.

**Safety rules:** unique anchor per replacement; strip linesegarray (automatic); verify before handing off.

```bash
# Example: renumber [10] → [11], [11] → [12] without cascade
# Pass multiple --replace flags (each uses TAB separator)
python3 skills/hwpx-edit/scripts/hwpx.py edit input.hwpx -o /dev/null --check \
  --replace "[10]	[T11]" \
  --replace "[11]	[T12]" \
  --replace "[T11]	[11]" \
  --replace "[T12]	[12]"

python3 skills/hwpx-edit/scripts/hwpx.py edit input.hwpx -o output_refs.hwpx \
  --replace "[10]	[T11]" \
  --replace "[11]	[T12]" \
  --replace "[T11]	[11]" \
  --replace "[T12]	[12]"

python3 skills/hwpx-edit/scripts/hwpx.py verify output_refs.hwpx
```

See `hwpx-internals.md` §Citations for the temp-token pattern and guidance on splitting the document at the reference-list heading before renumbering.

---

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
