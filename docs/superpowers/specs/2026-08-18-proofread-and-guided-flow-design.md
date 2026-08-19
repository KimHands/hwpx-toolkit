# hwpx-toolkit: 맞춤법 교정(proofread) + 가이드 작업 선택 플로우 — 설계 (rev3)

> 기존 hwpx-toolkit(읽기/추출·안전코어·메모·글자수델타·그림/수식·통합 CLI, 27 테스트)에 두 기능을 추가한다.
> rev1→rev2→rev3 = Codex·Fable 적대적 리뷰 2라운드 반영(실측 포함). 판정표 §E. 상위 규칙: `AGENTS.md`, `~/Ops/domains/hwp.md`.

## 목표
1. **proofread** — 한국어 맞춤법·문장 교정을 **손상 없이** 반영. 검사(언어 판단)=모델, 반영(결정론)=스크립트.
2. **가이드 작업 선택 플로우** — 하나의 흐름에서 원하는 작업을 체크리스트로 골라 순서대로 실행(스킬 레벨).

## 설계 원칙(기존 유지)
- 스크립트=결정론, 모델=판단. 런타임 **stdlib only**. **외부 발송 없음**. 원본 **in-place 금지**. 텍스트 변경 시 linesegarray strip. 쓰기 전 well-formed 검증.

---

## A. proofread — 맞춤법·문장 교정 반영

### A.1 좌표계 결정 (리뷰 rev1 M1/S1, rev2 이스케이프 자기모순 — **핵심**)
교정은 **본문 `<hp:t>` 노드의 "원문(raw) 내부 텍스트" 좌표계**에서만 일어난다. **언이스케이프하지 않는다.**
- **매칭**: `old`는 모델이 `extract --paragraphs`에서 본 문자열 **그대로**. `extract`(=`paragraph_texts`)는 엔티티를 언이스케이프하지 않으므로(`&gt;`, `&#8203;` 등이 그대로 보임), `old`도 그 표기 그대로 오며, 매칭은 본문 `<hp:t>` **원문 내부 문자열**에 대해 이뤄진다. → rev2의 "언이스케이프 평문 == paragraph_texts" 자기모순 제거, A.5 동치가 **라운드트립 없이 자명**.
- **치환**: **매칭된 스팬만 splice**. 노드의 나머지(다른 엔티티 포함)는 **바이트 그대로 보존**(rev2의 노드 전체 unescape→escape 오염 제거). 삽입되는 `new`만 `xml.sax.saxutils.escape(new)`(=`& < >`만 이스케이프)로 처리 → `new`로 마크업 주입 불가, well-formed 보존.
- **대상 제외**: 메모 subList 내부 `<hp:t>`, 태그·속성·필드 파라미터·수식 스크립트는 제외. 수식(`<hp:equation>`)은 `<hp:t>`가 아니라 자동 제외 → "수식 앵커 금지"가 기계적으로 성립.

### A.2 읽기 (기존 재사용)
모델은 `extract --paragraphs`로 번호 매긴 문단을 읽는다: `[0] …`, `[1] …`. 이 번호 = A.4 적용의 문단 번호(§A.5 동치 보장).

### A.3 라이브러리 (`_hwpxlib.py`에 추가 — 기존 `paragraph_texts`는 **미변경**, 리뷰 F2/O2)
- `enumerate_body_paragraphs(xml, eq_marker="⟨식⟩") -> list[dict]`
  각 **텍스트 보유 문단**을 `paragraph_texts`와 **동일 순서·필터**로 열거. 원소:
  `{"index": int, "display": str, "t_nodes": [(abs_start, abs_end), …]}` (`abs_*`=원본 xml 내 `<hp:t>`…`</hp:t>` **내부 텍스트**의 절대 오프셋).
  - **메모 마스킹 후 분할**(리뷰 rev1 F1, rev2에서 정본 규정): `strip_memo_sublists`와 **동일한 `_MEMO_SUBLIST` 정규식**으로 메모 스팬을 구해, **같은 길이의 `#` 반복 필러**(내부에 `<hp:p>`/`</hp:p>`/`<hp:t>`/`<hp:equation` 없음)로 치환한 사본에서 `<hp:p>` 경계를 분할 → 메모의 중첩 `<hp:p>`가 바깥 문단을 오절단 못함. 스팬은 **원본 좌표**로 복원. 마스킹 정규식이 `paragraph_texts`와 동일하므로 열거 동치가 성립.
  - `display`는 **`paragraph_texts`와 동일한 변환**(메모 제거 → `<hp:equation>`를 `eq_marker`로 **문서 순서 위치에** 치환 → 본문 `<hp:t>` 원문 이어붙임 → strip)을 그 문단 region에 적용해 만든다. (rev2 문언 "마커 뒤 덧붙임"은 오도 → "문서 순서 위치 삽입"으로 확정.)
  - `t_nodes` = 문단 region 안, **메모 스팬 밖**의 `<hp:t>` 내부 텍스트 오프셋 목록.
- `apply_paragraph_corrections(xml, corrections) -> (new_xml, results)`
  1. **입력 검증(먼저 전부)**: `corrections` 비어있으면 거부; 각 `p`는 정수 `0 ≤ p < 문단수`(bool·float·음수 거부); `old != ""`; `old != new`; 완전 동일 레코드 중복 거부.
  2. **계획(원본 상태 기준, 원자성)**: 각 교정에 대해 문단 `p`의 `t_nodes` **원문 텍스트** 전체에서 `old`가 **정확히 1회**이고 **단일 `t_node` 안**일 때만, 그 (노드, 문자 스팬)을 계획에 등록. 0회(런 경계 포함)·2회 이상·다중 노드 → `ValueError`(문단·count·old 명시).
  3. **겹침 검사(리뷰 S3)**: 계획된 스팬끼리 겹치면 `ValueError`. (스팬-splice 방식이라 rev2가 우려한 `str.replace`의 "new가 새 old 생성" 문제는 원천 제거.)
  4. **적용**: 모두 유효·비겹침일 때만, 계획된 스팬을 **절대 오프셋 내림차순**으로 splice(각 스팬을 `escape(new)`로 교체) → 앞 오프셋 유효성 유지, 부분 적용 없음.
  5. `results` = `{"p","old","new","delta"}`, `delta = len(new)-len(old)`(코드포인트, 정규화 없음 — §D).

### A.4 CLI (`hwpx.py`에 추가; 안전 파이프라인은 기존 `_write` 재사용, 리뷰 O1)
`proofread apply FILE -o OUT --from corrections.json [--check]`
- `--from`: JSON 배열 `[{"p":3,"old":"됬다","new":"됐다"}, …]`.
- 흐름: `read_section` → `apply_paragraph_corrections` → `strip_linesegarray` → `_write`(=`is_wellformed`+`repackage` to `-o`).
- 각 교정 `delta` 출력. `--check`: 계획+델타 계산 **및 is_wellformed까지 검증**하되 **파일 미기록**(적용 결과를 실제로 만들어 검증하고 버림).
- 오류·exit 2, **출력 파일 미생성**: `--from` 부재 / 루트가 배열 아님 / 필드 누락·타입 오류 / 매칭·겹침 실패. 적용 **전** 검증에서 문제 교정을 지목(늦은 minidom 오프셋 실패 아님).

### A.5 열거·좌표 동치 보장 (리뷰 rev1 F1, rev2 이스케이프)
A 최초 커밋에 실측 회귀 테스트 포함:
- `enumerate_body_paragraphs(xml)[i]["display"] == paragraph_texts(xml)[i]` — 레포 픽스처(메모·수식·하이퍼링크) **및** 엔티티 포함 문단(`&gt;`·`&#8203;` 등)을 담은 **별도 테스트 픽스처**로 고정(리뷰 rev2: 공허 통과 방지).
- `t_nodes` 오프셋이 실제 본문 `<hp:t>` 내부를 가리키고, 그 안에서 splice가 다른 엔티티를 **바이트 그대로 보존**함을 검증.

### A.6 안전·한계 (문서화)
- 기존 edit와 동일 안전 파이프라인(`_write`). 문단 내 유일·단일노드 앵커 강제.
- **런/필드 경계 한계(리뷰 rev2)**: `old`가 여러 `<hp:t>`(서식 분리·하이퍼링크 필드 경계 포함)에 걸치면 단일 노드 매칭 실패(count 0) → 안전 실패. 실제 문서는 서식마다 런이 갈리므로 **구절 단위 교정은 실패가 흔하다**. 단어 단위 맞춤법은 대개 한 런 안 → 안정. SKILL.md에 "실패 시 더 짧은 앵커/단어 단위로 재시도" 안내.
- **메모 내부 다른 필드 한계(리뷰 rev2, 기존 공통)**: `_MEMO_SUBLIST` 비탐욕이 메모 subList 속 다른 field에서 조기 종료 → 그 모양에서 메모 내용이 본문으로 열거될 수 있음. `paragraph_texts`와 **동일 정규식**이라 좌표 동치는 유지되나 "메모 제외" 약속이 깨지는 극단 케이스. §F 후속.
- **재포장 부분파일(리뷰 F4)**: 기존 전 명령 공통. §F.

---

## B. 가이드 작업 선택 플로우 (SKILL.md + references/workflows.md; 신규 런타임 코드 없음)

### B.1 동작
1. **사전 스캔**: `verify` + 필요시 `extract --memos/--equations`.
2. **다중선택 체크리스트**(하네스 질문 UI, 체크→submit): ☐ 확인(extract) ☐ 메모 제거(memo clear) ☐ 맞춤법·문장 교정(proofread) ☐ 글자수 델타 편집(edit) ☐ 그림 교체(figure swap) ☐ 수식 복제/첨자 복원(equation clone) ☐ 검증(verify). SKILL.md에는 특정 UI 위젯 비종속의 **개념 작업 목록**으로 서술.
3. **체이닝 실행**: 원본 → op1 `-o` v1 → op2 `-o` v2 → … → 최종. **번호 버전 파일 유지**(복구·디버깅용).
   - **신선도 규칙(리뷰 M3)**: 각 텍스트 변경 op 직전, **직전 산출물에서** 문단번호·앵커 재추출. 원본 기준 `p`/anchor를 뒤 단계 재사용 금지.
   - `figure swap`은 바이너리 교체 → strip/well-formed 비대상. "**텍스트 변경 op에만** 안전 파이프라인"임을 명시(리뷰 F5).
   - **중간 실패**: 마지막 성공 버전 보존 + 단계·사유 보고. 최종 `verify` 실패 시 산출물 보류·사람 판정.
4. 종료 시 `verify` + 델타 요약 + "HWP로 열어 확인(양성 '변조 가능성' 경고 가능)".
5. **no-op**: 대상 0건이면 건너뛰고 통지(빈 corrections는 proofread가 거부).

### B.2 산출물
`SKILL.md` "가이드 플로우" 절 + `references/workflows.md` 레시피(사전스캔→체크리스트→체이닝(신선도 재추출)→검증), 각 단계 안전 규칙 명시.

---

## C. 테스트
**proofread 라이브러리**(`tests/test_proofread.py`)
- **열거 동치**: `enumerate_body_paragraphs[i].display == paragraph_texts[i]` — 공유 픽스처 + **엔티티 포함 별도 픽스처**(리뷰 rev2).
- 본문 오타 교정(단일 노드 유일)만 정확 변경; 타 문단·마크업·메모 불변.
- **메모 안에만 있는 문자열** old → 본문 미존재 count 0 안전 실패(리뷰 S1).
- 본문+stringParam 동시 문자열 → 본문 `<hp:t>`만 세어 가짜 비유일 아님.
- `new`에 `<`/`&`/`>` → escape되어 well-formed 유지·표시상 해당 문자.
- **엔티티 보존**: 같은 노드에 `&#8203;`/`&gt;`가 있을 때 무관한 교정이 그 엔티티를 **바이트 그대로** 남김(리뷰 rev2 blocker 회귀 테스트).
- 런/필드 경계 old → count 0 안전 실패.
- 같은 문단 다중 교정 정상(내림차순 splice); 겹치는 스팬 → 거부.
- 입력 검증: 빈 배열·`old==""`·`old==new`·중복·범위밖/음수/float `p` 거부.
- delta 정확. 출력 well-formed. **기존 test_extract 회귀 없음**.

**proofread CLI E2E**(`tests/test_cli.py` 확장): `apply --from`(반영+strip+입력 불변), `--check`(미기록), `--from` 부재/불량 JSON/매칭 실패 → exit 2 + 출력 미생성.

**가이드 플로우**: 산문 — 자동 테스트 없음. workflows.md 명령이 실제 CLI와 일치하는지 문서 리뷰.

---

## D. 비목표 (YAGNI)
- 외부 맞춤법 API·로컬 형태소 사전 없음. `<hp:t>` 경계 넘는 앵커 미지원(안전 실패). CLI 대화형 TUI 없음. 문서 전체 일괄 치환 없음. 다중 섹션 미지원(`section0.xml`). 유니코드 정규화(NFC/NFD) 없음 — extract 출력 **그대로 복사**.

---

## E. 리뷰 판정 (Codex/Fable 2라운드)
| # | 지적(출처) | 분류 | 판정 | 조치 |
|---|---|---|---|---|
| 1 | 열거 불일치 naive split≠paragraph_texts (rev1, **실측**) | blocker | 수용 | 메모 마스킹 분할(A.3), rev2 실측으로 성립 확인 |
| 2 | 좌표계: raw XML count (rev1 S1/M1) | blocker | 수용 | 본문 `<hp:t>` 원문 좌표계(A.1) |
| 3 | `new`의 `<`/`&` 주입 (rev1 S2) | blocker | 수용 | 스팬-splice + `escape(new)`(A.1) |
| 4 | XML 이스케이프 책임 미배정 | blocker | 수용 | 스크립트=`saxutils.escape`(A.1/A.3) |
| 5 | display 리팩터 회귀 (F2/O2) | important | 수용 | `paragraph_texts` 미변경(A.3) |
| 6 | 다중교정·중복·겹침 (S3) | important | 수용 | 원본검증→겹침거부→내림차순 splice(A.3) |
| 7 | 원자성 | important | 수용 | 전부 검증 후 적용(A.3) |
| 8 | 체이닝 신선도 (M3) | important | 수용 | op 직전 재추출(B.1) |
| 9 | 스키마·빈배열·음수/float p·--from 부재 (M4) | important | 수용 | 입력 검증(A.3/A.4) |
| 10 | proofread vs edit --from (O1) | important | 부분수용/기각 | 별도 명령 유지, `_write` 재사용(A.4) |
| 11 | 재포장 부분파일 (F4) | minor | 수용(범위밖) | §F |
| 12 | figure swap 문구 (F5) | minor | 수용 | "텍스트 변경 op만"(B.1) |
| 13 | 중간파일 유지 | minor | 수용 | 번호 버전 파일(B.1) |
| 14 | NFC/NFD·마커 복사 (S5) | minor | 수용(문서화) | §D |
| 15 | `old==""`/`old==new` (S4) | minor | 수용 | 입력 검증(A.3) |
| 16 | **A.1↔A.5 이스케이프 자기모순: extract는 언이스케이프 안 함** (rev2, **실측**) | blocker | 수용 | 언이스케이프 폐지, 원문 매칭(A.1) |
| 17 | **노드 전체 라운드트립이 `&#8203;` 등 오염** (rev2, **실측**) | blocker | 수용 | 스팬만 splice, 나머지 바이트 보존(A.1) |
| 18 | memo 마스킹 정규식 정본 미지정 (rev2) | important | 수용 | `_MEMO_SUBLIST` 명시(A.3) |
| 19 | escape/unescape 함수 미지정 (rev2) | important | 수용 | 언이스케이프 없음 + `saxutils.escape`(A.1) |
| 20 | 다중 splice 오프셋 무효화 (rev2) | important | 수용 | 내림차순 splice(A.3-4) |
| 21 | 수식 마커 interleave 문언 오도 (rev2, 실측) | important | 수용 | "문서 순서 위치 삽입"(A.3) |
| 22 | 필드 경계 단일노드 실패 흔함 (rev2) | important | 수용(문서화) | A.6 한계 + SKILL 재시도 안내 |
| 23 | 메모 속 다른 필드 조기종료 (rev2) | minor | 수용(범위밖) | A.6/§F, 기존 공통 |
| 24 | `--check` 범위 모호 (rev2) | minor | 수용 | is_wellformed까지 검증·미기록(A.4) |
| 25 | mask-map-back 과함? (rev2) | — | 기각 | 양 리뷰 모두 "정당" 판정 |

## F. 후속(별도 작업)
- `repackage` 원자적 쓰기(temp + `os.replace`) — 전 명령 공통.
- 메모 subList 속 다른 field에서 `_MEMO_SUBLIST` 조기 종료 개선 — `paragraph_texts` 포함 공통.
