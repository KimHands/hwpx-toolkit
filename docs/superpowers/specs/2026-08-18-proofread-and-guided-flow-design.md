# hwpx-toolkit: 맞춤법 교정(proofread) + 가이드 작업 선택 플로우 — 설계 (rev2)

> 기존 hwpx-toolkit(읽기/추출·안전코어·메모·글자수델타·그림/수식·통합 CLI, 27 테스트)에 두 기능을 추가한다.
> rev2 = Codex·Fable 적대적 리뷰 반영. 판정표는 §E.
> 상위 규칙: `AGENTS.md`(안전 불변식), 도메인 규칙 `~/Ops/domains/hwp.md`.

## 목표
1. **proofread** — 한국어 맞춤법·문장 교정을 **손상 없이** 반영한다. 검사(언어 판단)는 모델이, 반영(결정론)은 스크립트가.
2. **가이드 작업 선택 플로우** — 하나의 흐름에서 원하는 작업들을 체크리스트로 골라 순서대로 실행한다(스킬 레벨).

## 설계 원칙(기존 유지)
- 스크립트=결정론, 모델=판단. 런타임 **stdlib only**. **외부 발송 없음**(맞춤법 API·네트워크 미사용).
- 원본 **in-place 금지**, 항상 `-o` 새 파일. 텍스트 변경 시 linesegarray strip. 쓰기 전 well-formed 검증.

---

## A. proofread — 맞춤법·문장 교정 반영

### A.1 좌표계 결정 (리뷰 M1/S1 핵심)
교정은 **본문 텍스트 좌표계**에서만 일어난다:
- 매칭·치환 대상 = 본문 `<hp:t>` 노드의 **언이스케이프된 평문**. 메모 subList 내부 `<hp:t>`, 태그·속성·필드 파라미터·수식 스크립트는 **대상에서 제외**.
- `old`는 모델이 `extract --paragraphs`에서 본 **평문 그대로**(엔티티 아님). `new`도 평문 — **스크립트가 `& < >`를 XML 이스케이프**해서 노드에 삽입(리뷰 M2). 따라서 `new`로 마크업 주입 불가 → well-formed·의미 보존이 구조적으로 보장(리뷰 S2 무력화).
- 이 결정으로 수식(`<hp:equation>`) 구간은 `<hp:t>`가 아니라 자동 제외 → "수식 앵커 금지" 규칙이 기계적으로 성립.

### A.2 읽기 (기존 재사용)
모델은 기존 `extract --paragraphs`로 번호 매긴 문단을 읽는다: `[0] …`, `[1] …`. 이 번호 = A.4 적용의 문단 번호(§A.5에서 동치 보장).

### A.3 라이브러리 (`_hwpxlib.py`에 추가 — 기존 `paragraph_texts`는 **건드리지 않음**, 리뷰 F2/O2)
- `enumerate_body_paragraphs(xml, eq_marker="⟨식⟩") -> list[dict]`
  각 **텍스트 보유 문단**을 `paragraph_texts`와 **동일한 순서·필터**로 열거. 원소:
  `{"index": int, "display": str, "t_nodes": [(abs_start, abs_end, plain_text), …]}`.
  - **메모 마스킹 후 분할**(리뷰 F1): 원본에서 MEMO `fieldBegin` 블록 스팬을 먼저 구해 **같은 길이의 무해 필러**(내부에 `<hp:p>`/`<hp:t>` 없음)로 치환한 사본으로 `<hp:p>` 경계를 분할 → 메모의 중첩 `<hp:p>`가 바깥 문단을 잘못 끊지 못함. 분할 스팬은 **원본 좌표**로 되돌려 사용.
  - 각 문단의 `t_nodes` = 그 문단 region 안, **메모 스팬 밖**의 `<hp:t>…</hp:t>` 목록. `plain_text` = 그 내부를 언이스케이프.
  - `display` = `t_nodes.plain` 이어붙임 + 수식 마커, strip. **`paragraph_texts`와 문자 그대로 일치**(§A.5 테스트로 고정).
- `apply_paragraph_corrections(xml, corrections) -> (new_xml, results)`
  `corrections` 원소 = `{"p": int, "old": str, "new": str}`.
  1. **입력 검증(먼저 전부)**: `corrections` 비어있으면 거부; 각 `p`는 정수이고 `0 ≤ p < 문단수`(bool·float·음수 거부); `old != ""`; `old != new`; 완전 동일 레코드 중복 거부.
  2. **매칭(원본 상태 기준, 원자성)**: 각 교정에 대해 문단 `p`의 `t_nodes` 평문 전체에서 `old` **정확히 1회**, 그리고 **단일 `t_node` 안**일 때만 계획에 등록. 0회(런 경계 포함)·2회 이상·다중 노드 → `ValueError`(문단·count·old 명시).
  3. **겹침 검사(리뷰 S3)**: 같은 노드 내 두 교정의 문자 스팬이 겹치면 `ValueError`.
  4. **적용**: 모든 교정이 유효·비겹침일 때만, 각 노드 평문에서 `old→new` 치환 후 **XML 이스케이프**하여 노드 내부 갱신. 부분 적용 없음.
  5. `results` = `{"p","old","new","delta"}`, `delta = len(new)-len(old)`(유니코드 코드포인트, NFC/NFD 정규화 안 함 — 모델은 extract 출력을 **그대로 복사**, §D 주의).

### A.4 CLI (`hwpx.py`에 추가; 안전 파이프라인은 기존 `_write` 재사용 — 사본 아님, 리뷰 O1)
`proofread apply FILE -o OUT --from corrections.json [--check]`
- `--from`: JSON 배열 `[{"p":3,"old":"됬다","new":"됐다"}, …]`.
- 흐름: `read_section` → `apply_paragraph_corrections` → `strip_linesegarray` → `_write`(=`is_wellformed`+`repackage` to `-o`).
- 각 교정 `delta` 출력. `--check`는 델타만, **파일 미기록**.
- 오류 처리·exit 2, **출력 파일 미생성**: `--from` 파일 없음 / JSON 루트가 배열 아님 / 필드 누락·타입 오류 / 매칭·겹침 실패. minidom 오프셋만 나오는 늦은 실패가 아니라 **적용 전 검증**에서 어떤 교정이 문제인지 지목.

### A.5 열거 동치 보장 (리뷰 F1)
`enumerate_body_paragraphs(xml)[i]["display"]` == `paragraph_texts(xml)[i]` 를 **레포 픽스처(메모·수식·하이퍼링크 포함)로 실측 고정**하는 테스트를 A 최초 커밋에 포함. 실측상 rev1의 naive split은 `[1]=이건 메모 주석이다`로 깨졌고(§E-1), 메모 마스킹으로 `[1]=앵커 본문…`으로 교정됨을 회귀 테스트로 못박는다.

### A.6 안전·한계 (문서화)
- 기존 edit와 동일 안전 파이프라인(`_write`). 문단 내 유일·단일노드 앵커 강제.
- **런 경계 한계**: `old`가 여러 `<hp:t>`에 걸치면 단일 노드 매칭 실패(count 0) → 안전 실패. 모델이 한 런 안 더 짧은 앵커로 재시도.
- **재포장 부분파일**(리뷰 F4): `repackage`가 `'w'`로 열어 중간 실패 시 부분 zip 가능 — 기존 전 명령 공통 이슈. 본 기능 범위 밖, §F 후속.

---

## B. 가이드 작업 선택 플로우 (SKILL.md + references/workflows.md; 신규 런타임 코드 없음)

### B.1 동작
1. **사전 스캔**: `verify`(메모/하이퍼링크/수식 수) + 필요시 `extract --memos/--equations`.
2. **다중선택 체크리스트**(하네스 질문 UI, 체크→submit):
   ☐ 확인(extract) ☐ 메모 제거(memo clear) ☐ 맞춤법·문장 교정(proofread) ☐ 글자수 델타 편집(edit) ☐ 그림 교체(figure swap) ☐ 수식 복제/첨자 복원(equation clone) ☐ 검증(verify)
3. **체이닝 실행**: 원본 → op1 `-o` v1 → op2 `-o` v2 → … → 최종. **번호 붙인 버전 파일을 남긴다**(임시삭제 아님 — 디버깅·복구, 리뷰 과잉설계 minor). 
   - **신선도 규칙(리뷰 M3)**: 각 텍스트 변경 op 직전, **직전 산출물에서 문단번호·앵커를 재추출**(앞 op가 열거를 바꿨을 수 있음). 원본에서 뽑은 `p`/anchor를 뒤 단계에 재사용 금지.
   - `figure swap`은 바이너리 교체라 strip/well-formed 대상 아님(리뷰 F5) — "텍스트 변경 op"에만 안전 파이프라인이 적용됨을 명시.
   - **중간 실패**: 마지막 성공 버전까지 보존, 어느 단계·왜 멈췄는지 보고. 최종 `verify` 실패 시 산출물 제공 보류하고 사람에게 판정 요청.
4. 종료 시 `verify` + 델타 요약 + "HWP로 열어 확인(양성 '변조 가능성' 경고 가능)".
5. **no-op 처리(리뷰 minor)**: 선택했지만 대상 0건(메모 0개 / corrections 빈 배열)이면 그 단계는 건너뛰고 사용자에게 통지(빈 corrections는 proofread가 애초에 거부, §A.3-1).

### B.2 산출물
- `SKILL.md`에 "가이드 플로우(작업 선택)" 절. `references/workflows.md`에 사전스캔→체크리스트→체이닝(신선도 재추출 포함)→검증 레시피. 각 단계가 의존하는 안전 규칙 명시.
- SKILL.md의 체크리스트는 **개념 작업 목록**으로 서술(특정 UI 위젯에 종속되지 않게 — 리뷰 minor).

---

## C. 테스트
**proofread 라이브러리**(`tests/test_proofread.py`)
- **열거 동치**: `enumerate_body_paragraphs[i].display == paragraph_texts[i]` (픽스처의 메모·수식·하이퍼링크 문단 포함) — §A.5.
- 본문 오타 교정(단일 노드 유일)만 정확히 변경; 타 문단·마크업·메모 불변.
- **메모 안에만 있는 문자열**을 old로 주면 본문 미존재 → count 0 안전 실패(리뷰 S1).
- 본문+stringParam 동시 존재 문자열 → 가짜 비유일 아님 확인(본문 `<hp:t>`만 셈).
- `new`에 `<`,`&`,`>` 포함 → 이스케이프되어 well-formed 유지, 표시상 그 문자로 보임(리뷰 S2).
- 런 경계 old → count 0 안전 실패(리뷰 F3/A.6).
- 같은 문단 다중 교정 정상; 겹치는 스팬 → 거부(리뷰 S3).
- 입력 검증: 빈 배열·`old==""`·`old==new`·중복 레코드·범위밖/음수/float `p` 거부(리뷰 M4).
- delta 정확(코드포인트). 출력 well-formed. **기존 test_extract 회귀 없음**(paragraph_texts 미변경).

**proofread CLI E2E**(`tests/test_cli.py` 확장)
- `proofread apply --from`: 교정 반영 + linesegarray strip + **입력 파일 불변**.
- `--check`: 파일 미기록. `--from` 파일 없음 / 불량 JSON / 매칭 실패 → exit 2 + 출력 파일 미생성.

**가이드 플로우**: 산문(모델 오케스트레이션) — 자동 테스트 없음. workflows.md 명령 예시가 실제 CLI 형태와 일치하는지 문서 리뷰.

---

## D. 비목표 (YAGNI)
- 외부 맞춤법 API·로컬 형태소 사전 없음(검사는 모델).
- `<hp:t>` 런 경계를 넘는 앵커 지원 안 함(안전 실패).
- CLI 대화형 TUI 없음(선택 플로우는 스킬 레벨).
- 문서 전체 반복어 일괄 치환 없음(문단·단일노드 스코프).
- 다중 섹션(section1.xml+) 지원 안 함(`Contents/section0.xml` 스코프 유지).
- 유니코드 정규화(NFC/NFD) 안 함 — 모델은 extract 출력을 **그대로 복사**(주의로 문서화).

---

## E. 리뷰 판정 (Codex/Fable rev1 → rev2 반영)
| # | 지적(출처) | 분류 | 판정 | 근거/조치 |
|---|---|---|---|---|
| 1 | 열거 불일치: naive split ≠ paragraph_texts, 픽스처에서 `[1]`이 메모 주석 (Codex·Fable, **실측 재현**) | blocker | **수용** | 메모 마스킹 후 분할(A.3). A.5 회귀 테스트로 고정 |
| 2 | 좌표계 불일치: `block.count(old)`가 raw XML을 셈 (Codex S1·Fable M1) | blocker | **수용** | 본문 `<hp:t>` 평문 좌표계로 재설계(A.1/A.3) |
| 3 | `new`의 `<`/`&`가 well-formed 깨거나 마크업 주입 (Codex·Fable S2) | blocker | **수용** | 스크립트가 XML 이스케이프해 텍스트 노드 삽입(A.1). 주입 불가 |
| 4 | XML 이스케이프 책임 미배정 (M2) | blocker | **수용** | 스크립트 책임으로 명시(A.1) |
| 5 | `paragraph_display_text` "동작 불변" 불가·회귀 위험 (F2/O2) | important | **수용** | 리팩터 폐기, `paragraph_texts` 미변경(A.3) |
| 6 | 다중 교정 순서·중복 `p`·겹침 미명세 (S3) | important | **수용** | 원본 기준 검증→겹침 거부→일괄 적용(A.3-2~4) |
| 7 | 원자성(부분 적용) 불명확 | important | **수용** | 전부 검증 후 적용, 부분 없음(A.3) |
| 8 | 체이닝 신선도(앞 op가 열거 변경) (M3) | important | **수용** | 각 op 직전 재추출 규칙(B.1-3) |
| 9 | 스키마 검증·빈 배열·음수/float `p`·`--from` 부재 (M4) | important | **수용** | 입력 검증 명세(A.3-1, A.4) |
| 10 | 별도 `proofread` vs `edit --from` (O1) | important | **부분수용/기각** | 별도 명령 유지(용도·매칭 의미 상이). 단 안전 파이프라인은 기존 `_write` 재사용 → 사본 없음(A.4) |
| 11 | 재포장 부분파일(temp+rename 없음) (F4) | minor | **수용(범위밖)** | 사실, 전 명령 공통. §F 후속 항목으로 기록 |
| 12 | figure swap "동일 파이프라인" 부정확 (F5) | minor | **수용** | "텍스트 변경 op만" 문구 수정(B.1-3, A.6) |
| 13 | 중간파일 임시삭제 과함, 단계 파일 유지가 현실적 | minor | **수용** | 번호 버전 파일 유지(B.1-3) |
| 14 | NFC/NFD·`⟨식⟩` 마커 복사 오염 (S5) | minor | **수용(문서화)** | 정규화 안 함, extract 그대로 복사 주의(§D) |
| 15 | `old==""`·`old==new` no-op 미정의 (S4) | minor | **수용** | 입력 검증에서 거부(A.3-1) |

## F. 후속(별도 작업)
- `repackage` 원자적 쓰기(temp 파일 + `os.replace`)로 중간 실패 시 부분 zip 방지 — 전 명령 공통 개선, 본 기능과 분리.
