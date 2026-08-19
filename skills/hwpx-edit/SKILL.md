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
- `proofread apply FILE -o OUT --from corrections.json [--check]` — 문단 스코프
  맞춤법·문장 교정. corrections = `[{"p":문단번호,"old":"오타","new":"교정"}]`.
  `p`는 `extract --paragraphs`의 `[i]` 번호. `old`는 그 출력에 보인 **문자 그대로**
  (엔티티 `&gt;`·`&#8203;` 포함) 복사. `old`는 해당 문단 안에서 유일해야 하고 한
  `<hp:t>` 런 안에 있어야 한다(런 경계를 넘으면 안전 실패 → 더 짧은 단어 단위로 재시도).
  `--check`로 먼저 델타를 확인한 뒤 적용.

## Non-negotiable rules
1. Never edit the original in place — always `-o` a new version (bump the ver number).
2. The CLI repackages by structure-clone; never shell `zip`.
3. Text changes strip all linesegarray (CLI does this) so HWP recomputes layout.
4. `edit` anchors MUST be unique. Choose anchors in **pure Korean** runs — never
   spanning an `<hp:equation>` or containing `&gt;` (the XML escape for `>`).
5. You (the model) craft the replacement text: meaning-preserving, hitting the
   requested character delta; the CLI reports the delta so you can check.

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

## Limitation
The environment cannot render HWPX. After editing, tell the author to open the
file in HWP and eyeball layout (a benign "변조 가능성" warning may appear).
See references/hwpx-internals.md and references/workflows.md.
