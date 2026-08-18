# hwpx-toolkit: 맞춤법 교정(proofread) + 가이드 작업 선택 플로우 — 설계

> 기존 hwpx-toolkit(읽기/추출·안전코어·메모·글자수델타·그림/수식·통합 CLI, 27 테스트)에 두 기능을 추가한다.
> 상위 규칙: `AGENTS.md`(안전 불변식), 도메인 규칙 `~/Ops/domains/hwp.md`.

## 목표
1. **proofread** — 한국어 맞춤법·문장 교정을 **손상 없이** 반영한다. 검사(언어 판단)는 모델이, 반영(결정론)은 스크립트가.
2. **가이드 작업 선택 플로우** — 하나의 흐름에서 원하는 작업들을 체크리스트로 골라 순서대로 실행한다(스킬 레벨).

## 설계 원칙(기존 유지)
- 스크립트=결정론(재포장·추출·유일성검사·델타·strip·검증), 모델=판단(오류 식별·교정 문구·앵커 선택).
- 런타임 **stdlib only**. **외부 발송 없음**(맞춤법 API·네트워크 미사용) — 안전 게이트·프라이버시 준수.
- 원본 **in-place 금지**, 항상 `-o` 새 파일. 텍스트 변경 시 linesegarray strip. 쓰기 전 well-formed 검증.

---

## A. proofread — 맞춤법·문장 교정 반영

### A.1 읽기 (기존 재사용)
모델은 기존 `extract --paragraphs`로 번호 매긴 문단을 읽는다: `[0] …`, `[1] …`.
이 번호 = proofread 적용의 문단 번호와 **동일 체계**(아래 A.3에서 보장).

### A.2 라이브러리 (`skills/hwpx-edit/scripts/_hwpxlib.py`에 추가)
- `paragraph_display_text(block: str, eq_marker="⟨식⟩") -> str`
  단일 `<hp:p>` 블록의 표시 텍스트(메모 subList 제거 → 수식 마커 치환 → `<hp:t>` 연결 → strip).
  기존 `paragraph_texts`를 이 헬퍼를 쓰도록 리팩터(DRY). 동작 불변.
- `apply_paragraph_corrections(xml: str, corrections: list[dict]) -> tuple[str, list[dict]]`
  `corrections` 각 원소 = `{"p": int, "old": str, "new": str}`.
  - 원본 `xml`의 `<hp:p>` 블록을 **문서 순서**로 순회하며, `paragraph_display_text(block)`가 비어있지 않은 블록에만 0,1,2… 인덱스를 부여(= `paragraph_texts` 열거와 동일).
  - 인덱스 `p`의 블록에 대해, 각 교정의 `old`가 그 블록 안에서 **정확히 1회**(`block.count(old)==1`)일 때만 적용. 아니면 `ValueError`(문단번호·count·old 명시), **아무것도 쓰지 않음**.
  - `p`가 존재하는 텍스트 문단 인덱스 범위를 벗어나면 `ValueError`.
  - 결과 레코드 `{"p","old","new","delta"}`, `delta = len(new)-len(old)`(유니코드 코드포인트).
  - 위치 기반 재조립(스팬 이어붙이기)으로 **동일 블록 문자열 중복 시에도 안전**(`str.replace` 전역치환 금지).

### A.3 열거 일치 보장
`apply_paragraph_corrections`의 인덱싱 술어·순서는 `paragraph_texts`와 동일해야 한다. 테스트로 고정:
`extract --paragraphs`의 `[i]` 텍스트와, 인덱스 `i`에 교정을 넣었을 때 실제로 바뀌는 문단이 일치.

### A.4 CLI (`skills/hwpx-edit/scripts/hwpx.py`에 추가)
`proofread apply FILE -o OUT --from corrections.json [--check]`
- `--from`: JSON 배열 파일 `[{"p":3,"old":"됬다","new":"됐다"}, …]`(문장부호·탭·개행에 견고).
- 흐름: `read_section` → `apply_paragraph_corrections` → `strip_linesegarray` → `is_wellformed` → `repackage` to `-o`.
- 각 교정의 `delta`를 사람이 읽게 출력. `--check`는 델타만 출력하고 **파일 미기록**.
- 오류(비유일·범위밖·불량 JSON) 시 stderr + 비정상 종료(코드 2), **출력 파일 미생성**.

### A.5 안전·한계
- 기존 edit와 동일 안전 파이프라인. 문단 내 유일 앵커 강제.
- 모델은 수식(HancomEQN)·`&gt;` 이스케이프 구간을 앵커로 쓰지 않는다(SKILL.md 가이드).
- **런 경계 한계**: `old`가 여러 `<hp:t>` 런에 걸치면 `count==0` → 안전 실패(ValueError). 모델이 한 런 안의 더 짧은 앵커로 재시도. (기존 edit와 동일 제약, 문서화)

---

## B. 가이드 작업 선택 플로우 (SKILL.md + references/workflows.md; 신규 런타임 코드 없음)

### B.1 동작
`.hwpx` 편집 요청이 여러 작업을 포함할 수 있을 때, 모델은:
1. **사전 스캔**: `verify`(메모/하이퍼링크/수식 중복 수) + 필요시 `extract --memos/--equations`로 문서에 무엇이 있는지 파악.
2. **다중선택 체크리스트 제시**(하네스의 질문 UI로 체크→submit):
   - ☐ 본문/메모/수식 확인(extract) ☐ 메모 전체 제거(memo clear) ☐ 맞춤법·문장 교정(proofread)
   - ☐ 글자수 델타 편집(edit) ☐ 그림 교체(figure swap) ☐ 수식 복제/첨자 복원(equation clone) ☐ 검증(verify)
3. **체이닝 실행**: 원본 → op1 `-o` v1 → op2 `-o` v2 → … → 최종. 중간 파일은 임시, **마지막 파일만 산출물**. 각 쓰기 작업은 CLI가 안전 파이프라인을 강제.
4. 종료 시 `verify` 실행, 델타 요약 + "HWP로 열어 레이아웃 확인(양성 '변조 가능성' 경고 가능)" 안내.

### B.2 산출물
- `SKILL.md`에 "가이드 플로우(작업 선택)" 절 추가.
- `references/workflows.md`에 구체 명령 예시가 있는 레시피 1건 추가(사전스캔→체크리스트→체이닝→검증). 각 단계가 의존하는 안전 규칙 명시.

---

## C. 테스트
**proofread 라이브러리**(`tests/test_proofread.py`)
- 문단 스코프 적용(문단 내 유일 old)로 정확한 문단만 변경.
- 문단 내 비유일 old → ValueError, 미기록.
- 범위 밖 `p` → ValueError.
- delta 정확(유니코드 코드포인트).
- 열거 일치: `paragraph_texts` 인덱스와 apply 대상 문단 일치(메모/수식 포함 문단 포함).
- 타 문단 불변, 출력 well-formed.
- `paragraph_display_text` 리팩터 후 `paragraph_texts` 회귀 없음(기존 test_extract 유지).

**proofread CLI E2E**(`tests/test_cli.py` 확장)
- `proofread apply --from`: 출력에 교정 반영 + linesegarray strip + **입력 파일 불변**.
- `--check`: 파일 미기록, 델타 출력.
- 불량 교정(비유일/범위밖/불량 JSON): 비정상 종료 + 출력 파일 미생성.

**가이드 플로우**: 산문(모델 오케스트레이션) — 자동 테스트 없음. workflows.md 명령 예시가 실제 CLI 형태와 일치하는지 문서 리뷰로 확인.

---

## D. 비목표 (YAGNI)
- 외부 맞춤법 API·로컬 형태소 사전 없음(검사는 모델 몫).
- `<hp:t>` 런 경계를 넘는 앵커 지원 안 함(안전 실패로 처리).
- CLI 대화형 TUI 메뉴 없음(선택 플로우는 스킬 레벨).
- 문서 전체 반복어 일괄 치환 모드 없음(문단 스코프만).
- 다중 섹션(section1.xml+) 지원 안 함(기존 스코프 유지: `Contents/section0.xml`).

---

## E. 리뷰 판정 (Codex/Fable — 확정 전 채움)
| # | 지적(출처) | 분류 | 판정 | 근거/조치 |
|---|---|---|---|---|
| | | | | |
