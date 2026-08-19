<!-- 한국어: this file | English: [README.en.md](README.en.md) -->

# hwpx-toolkit

한글(HWPX) 문서를 **손상 없이 읽고 편집**하는 워크플로우. ZIP 구조를 깨뜨리거나 글자가 겹쳐 보이는 문제 없이 안전하게 편집한다. Claude Code 플러그인 · Codex 스킬로 패키징돼 있다. (MIT, 공개)

## 무엇인가

HWPX는 OWPML XML을 담은 ZIP 컨테이너다. 손대면 위험한 함정이 둘 있다: 한글(HWP)은 아무렇게나 재포장한 ZIP을 **열지 못하고**, 문단의 줄 위치 캐시(`linesegarray`)가 남아 있으면 **글자가 겹쳐** 렌더링된다. 이 스킬이 두 문제를 자동으로 처리한다.

역할 분담이 명확하다 — **스크립트는 결정론적 작업**(재포장·추출·유일성 검사·글자수 델타·strip·검증)을, **모델(Claude)은 언어 판단**(오류 식별·교정 문구 작성·앵커 선택)을 맡는다.

### 할 수 있는 일

| 작업 | 설명 |
|---|---|
| 본문·메모·수식 읽기 | 본문 문단 · 검토자 메모 · 수식 스크립트 추출 |
| 메모 제거 | 검토자 메모 전체 제거(본문·하이퍼링크는 보존) |
| 글자수 델타 편집 | 유일 앵커로 텍스트 치환, 치환별 글자수 델타 보고(과부/위도 조정 등) |
| **맞춤법·문장 교정** | 문단 스코프로 오타·띄어쓰기 교정을 안전하게 반영 |
| 그림 교체 | 내장 PNG를 슬롯 이름으로 교체(종횡비 맞춤) |
| 수식 복제/첨자 복원 | 첨자 항을 `<hp:equation>` 객체로 복원 |
| 검증 | 파일 넘기기 전 구조 검증 |
| 가이드 플로우 | 여러 작업을 체크리스트로 골라 한 흐름에 이어 실행 |

## 사용법 — Claude Code (기본)

플러그인을 설치하면 **CLI를 직접 칠 필요가 없다.** Claude Code 대화창에서 하고 싶은 작업을 그냥 말하면 `hwpx-edit` 스킬이 활성화되고, 도구가 안전하게 실행된다. 명시적으로 부르려면 대화창에 **`/hwpx-edit`** 를 입력한다.

대화창에 이렇게 입력하면 된다:

```
이 논문.hwpx 맞춤법 좀 고쳐줘
```
```
메모 다 지우고 v2로 저장해줘
```
```
3장이랑 4장 순서 바꾸고 참고문헌 appearance 순으로 다시 번호 매겨줘
```
```
/hwpx-edit   (스킬을 명시적으로 호출)
```

그러면 Claude가 알아서: 본문·문단을 읽고 → 교정·편집안을 만들고 → 문단 스코프로 안전하게 적용하고 → 검증한 뒤 **새 파일로 저장**한다. 원본은 절대 덮어쓰지 않는다. 편집이 끝나면 한글(HWP)로 열어 레이아웃을 확인하라고 안내한다(양성 "변조 가능성" 경고가 나타날 수 있음).

### 설치 — Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-edit
```

### 설치 — Codex

[`codex/install.md`](codex/install.md) 참고. Codex에서도 같은 `hwpx-edit` 스킬이 뜨고, 대화로 동일하게 사용한다.

## 안전 보장

편집이 어떤 경로로 일어나든 아래는 항상 지켜진다:

1. **원본 in-place 금지** — 항상 새 파일로 저장한다. 원본은 절대 건드리지 않는다.
2. **구조 복제 재포장** — `mimetype` 엔트리 최초 · STORED 압축 · 디렉터리 엔트리 0. 셸 `zip`을 쓰지 않는다.
3. **linesegarray 제거** — 텍스트 변경 때마다 오래된 줄 캐시를 모두 지워, 한글이 열 때 레이아웃을 새로 계산하게 한다.
4. **well-formed 검증** — 저장 전에 XML 유효성을 검사한다.
5. **유일 앵커** — 앵커가 여러 번 일치하면 적용을 거부한다. 맞춤법 교정은 각 `old`가 **해당 문단 안에서 유일**하고 **한 텍스트 런 안**에 있어야 한다.
6. **본문 텍스트 좌표계만** — 맞춤법 교정은 본문 텍스트 안에서만 매칭·치환하고 교정 문구만 XML 이스케이프하므로, 주변 엔티티(`&gt;`·`&#8203;` 등)가 바이트 그대로 보존되고 마크업 주입이 불가능하다. 앵커는 `<hp:equation>`이나 `&gt;` 이스케이프 구간을 넘지 않는다.

## CLI 직접 실행 (선택 · 자동화/기여자용)

스킬이 내부에서 쓰는 CLI를 직접 실행할 수도 있다. 자동화 스크립트나 디버깅에 유용하다.

```bash
# 번호 매긴 문단 읽기
python3 skills/hwpx-edit/scripts/hwpx.py extract 논문.hwpx --paragraphs
#   → [0] …  [1] …  (여기 번호가 아래 교정의 p 값)

# 맞춤법 교정: corrections.json = [{"p":3,"old":"됬다","new":"됐다"}]
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o 논문_v2.hwpx --from corrections.json --check   # 미리보기(파일 안 씀)
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o 논문_v2.hwpx --from corrections.json           # 적용

# 메모 제거 / 검증
python3 skills/hwpx-edit/scripts/hwpx.py memo clear 초안.hwpx -o 초안_정리.hwpx
python3 skills/hwpx-edit/scripts/hwpx.py verify 논문_v2.hwpx
```

전체 서브커맨드: `extract` · `memo clear` · `edit` · `proofread apply` · `figure swap` · `equation clone` · `verify` · `repackage`.

## 기여자용

프로젝트 venv로 전체 테스트를 실행한다:

```bash
.venv/bin/pytest -v
```

macOS 시스템 파이썬은 외부 관리(PEP 668)라 pytest 직접 설치가 막혀 있어, 테스트는 프로젝트 venv(`.venv/`)가 정본이다. 없으면 `python3 -m venv .venv && .venv/bin/pip install pytest`로 다시 만든다. 테스트 **43개 전부 통과**해야 한다(런타임은 순수 Python 3.9+ stdlib).

## 라이선스

MIT — [LICENSE](LICENSE) 참고.
