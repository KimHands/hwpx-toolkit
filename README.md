<!-- 한국어: this file | English: [README.en.md](README.en.md) -->

# hwpx-toolkit

한글(HWPX) 문서를 명령줄에서 **손상 없이 읽고 편집**하는 도구. ZIP 구조를 깨뜨리거나 글자가 겹쳐 보이는 문제 없이 안전하게 편집한다. Claude Code 플러그인 · Codex 스킬로 패키징돼 있다. (MIT, 공개)

## 무엇인가

HWPX는 OWPML XML을 담은 ZIP 컨테이너다. 손대면 위험한 함정이 둘 있다: 한글(HWP)은 아무렇게나 재포장한 ZIP을 **열지 못하고**, 문단의 줄 위치 캐시(`linesegarray`)가 남아 있으면 **글자가 겹쳐** 렌더링된다. 이 도구의 CLI(`hwpx.py`)가 두 문제를 자동으로 처리한다.

역할 분담이 명확하다 — **스크립트는 결정론적 작업**(재포장·추출·유일성 검사·글자수 델타·strip·검증)을, **모델(Claude)은 언어 판단**(오류 식별·교정 문구 작성·앵커 선택)을 맡는다.

### 지원 작업

| 작업 | 설명 |
|---|---|
| `extract` | 본문 문단 · 메모 · 수식 스크립트 읽기 |
| `memo clear` | 검토자 메모 전체 제거(본문·하이퍼링크는 보존) |
| `edit` | 유일 앵커로 텍스트 치환, 치환별 글자수 델타 보고 |
| `proofread apply` | **문단 스코프 맞춤법·문장 교정** — JSON 파일로 일괄 반영(모델이 오류를 찾고, 스크립트가 안전하게 적용) |
| `figure swap` | 슬롯 이름으로 내장 PNG 교체 |
| `equation clone` | 첨자 항을 `<hp:equation>` 객체로 복원 |
| `verify` | 파일 넘기기 전 구조 검증 게이트 |
| `repackage` | (저수준) 수정된 아카이브 엔트리로 ZIP 재조립 |

여기에 **가이드 작업 선택 플로우**(스킬 레벨)가 있다: 문서를 사전 스캔하고, 작업 다중선택 체크리스트를 제시한 뒤, 고른 작업들을 하나의 파이프라인으로 이어 실행한다(각 단계 직전 재추출로 신선도 유지).

## 안전 보장

1. **원본 in-place 금지** — 항상 `-o`로 새 파일에 쓴다. 원본은 절대 건드리지 않는다.
2. **구조 복제 재포장** — `mimetype` 엔트리 최초 · STORED 압축 · 디렉터리 엔트리 0. 셸 `zip`을 쓰지 않는다.
3. **linesegarray 제거** — 텍스트 변경 때마다 오래된 줄 캐시를 모두 지워, 한글이 열 때 레이아웃을 새로 계산하게 한다.
4. **well-formed 검증** — 출력 파일을 쓰기 전에 XML 유효성을 검사한다.
5. **유일 앵커** — `edit`는 앵커가 2회 이상 일치하면 적용을 거부한다. `proofread`는 각 `old`가 **해당 문단 안에서 유일**하고 **한 `<hp:t>` 런 안**에 있어야 한다.
6. **본문 텍스트 좌표계만** — `proofread`는 본문 `<hp:t>` 텍스트 안에서만 매칭·치환하고, 삽입되는 교정 문구만 XML 이스케이프한다. 그래서 주변 엔티티(`&gt;`·`&#8203;` 등)가 바이트 그대로 보존되고 마크업 주입이 불가능하다. 앵커는 `<hp:equation>`이나 `&gt;` 이스케이프 구간을 넘지 않는다.

## 설치 — Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-edit
```

설치 후, `.hwpx` 편집 작업에는 `hwpx-edit` 스킬을 사용한다.

## 설치 — Codex

[`codex/install.md`](codex/install.md) 참고.

## 사용 예

**초안에서 메모 전체 제거:**

```bash
python3 skills/hwpx-edit/scripts/hwpx.py memo clear 초안.hwpx -o 초안_정리.hwpx
```

**맞춤법·문장 교정(proofread):**

```bash
# 1) 번호 매긴 문단 읽기
python3 skills/hwpx-edit/scripts/hwpx.py extract 논문.hwpx --paragraphs
#   → [0] …  [1] …  형태로 출력. 여기 번호가 아래 p 값이다.

# 2) corrections.json 작성 (old 는 위 출력에 보인 문자 그대로 복사)
#   [{"p": 3, "old": "됬다", "new": "됐다"},
#    {"p": 7, "old": "할수있다", "new": "할 수 있다"}]

# 3) 미리보기 — 글자수 델타만 출력하고 파일은 안 씀
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o /tmp/미리보기.hwpx --from corrections.json --check

# 4) 실제 적용
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o 논문_v2.hwpx --from corrections.json

# 5) 검증
python3 skills/hwpx-edit/scripts/hwpx.py verify 논문_v2.hwpx
```

`old`가 문단 안에서 유일하지 않거나 여러 `<hp:t>` 런에 걸치면 오류로 안전하게 멈춘다 → 더 짧은 단어 단위 앵커로 다시 시도한다.

**글자수 델타 편집(과부/위도 조정 등):**

```bash
# --replace 는 old<TAB>new — old 와 new 사이는 리터럴 탭 문자
python3 skills/hwpx-edit/scripts/hwpx.py edit 초안.hwpx -o /dev/null \
  --replace "논문의 특유한 구절이다	논문의 짧은 구절" --check
```

## 편집 환경 안내

- 이 환경은 HWPX를 렌더링하지 못한다. 편집 후에는 저자가 한글(HWP)로 파일을 열어 레이아웃을 눈으로 확인해야 한다(양성 "변조 가능성" 경고가 나타날 수 있음).
- `proofread`의 문단 번호 `p`는 반드시 **직전 산출물**에서 `extract --paragraphs`로 다시 뽑는다(앞 작업이 문단 열거를 바꿨을 수 있음).

## 기여자용

프로젝트 venv로 전체 테스트를 실행한다:

```bash
.venv/bin/pytest -v
```

macOS 시스템 파이썬은 외부 관리(PEP 668)라 pytest 직접 설치가 막혀 있어, 테스트는 프로젝트 venv(`.venv/`)가 정본이다. 없으면 `python3 -m venv .venv && .venv/bin/pip install pytest`로 다시 만든다.

테스트 **43개 전부 통과**해야 한다. 테스트는 `tests/`에 있고 Python 3.9+ 표준 라이브러리 + pytest만 필요하다(런타임은 순수 stdlib).

## 라이선스

MIT — [LICENSE](LICENSE) 참고.
