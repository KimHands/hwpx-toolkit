<!-- 한국어: this file | English: [README.en.md](README.en.md) -->

<div align="center">

# 📝 hwpx-toolkit

**한글(HWPX) 문서를 손상 없이 읽고 편집하는 Claude Code · Codex 스킬**

*.hwpx는 예민한 zip 구조라 아무렇게나 저장하면 한글이 파일을 안 엽니다.*
*이 스킬은 구조를 그대로 복제해 재포장하고 오래된 줄 캐시를 지워, 대화만으로 편집을 진행합니다.*

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![deps](https://img.shields.io/badge/deps-stdlib_only-success)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8A63D2)
![Codex](https://img.shields.io/badge/Codex-skill-000000)
[![tests](https://github.com/KimHands/hwpx-toolkit/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/KimHands/hwpx-toolkit/actions/workflows/test.yml)
![License](https://img.shields.io/badge/License-MIT-black)

</div>

> **범위 포지셔닝** — hwpx-toolkit은 새 문서를 만들거나 PDF·docx로 **변환하지 않습니다**.
> 이미 있는 `.hwpx`를 **손상 없이 편집하고 새 버전으로 저장**하는 도구입니다. 원본은 절대 건드리지 않습니다.

---

## ✨ 주요 기능

- **맞춤법·문장 교정 (proofread)** — 본문 텍스트만 문단 스코프로 안전하게 교정. 주변 엔티티·마크업은 바이트 그대로 보존
- **검토 메모 일괄 제거** — 교수님/리뷰어 메모를 모두 제거하되 본문·하이퍼링크는 보존
- **글자수 델타 편집** — 유일 앵커로 텍스트를 치환하고 치환별 글자수 변화를 보고(과부/위도 조정)
- **그림 교체 · 수식 복제** — 내장 PNG를 슬롯 이름으로 교체, 첨자 항을 `<hp:equation>` 객체로 복원
- **읽기 / 검증** — 본문·메모·수식 추출, 넘기기 전 구조 검증
- **가이드 작업 선택 플로우** — 여러 작업을 체크리스트로 골라 한 흐름에 이어 실행
- **스크립트=결정론, 모델=판단** — 재포장·검증·글자수는 스크립트가, 오류 식별·교정 문구는 모델이 담당

---

## 💬 사용법 — Claude Code

플러그인을 설치하면 **CLI를 직접 칠 필요가 없습니다.** 대화창에 **자연어로 말하면** `hwpx-edit` 스킬이 자동 활성화됩니다(가장 확실한 방법).

```
이 논문.hwpx 맞춤법 좀 고쳐줘
메모 다 지우고 v2로 저장해줘
이 문장을 다음처럼 바꾸고 글자수 변화도 알려줘
```

슬래시 메뉴로도 부를 수 있습니다 — `/` 를 누르고 `hwpx` 를 입력하면 목록에 뜹니다. 이름은 설치 방식에 따라 다릅니다: 플러그인은 **`hwpx-toolkit:hwpx-edit`**, 개인 스킬(`~/.claude/skills/hwpx-edit/`)은 `/hwpx-edit`.

Claude가 알아서: 본문·문단을 읽고 → 교정·편집안을 만들고 → 문단 스코프로 안전 적용 → 검증 → **새 파일로 저장**합니다. 끝나면 한글(HWP)로 열어 확인하라고 안내합니다(양성 "변조 가능성" 경고가 나타날 수 있음).

---

## 🔍 편집 전후 사례

아래는 테스트용 합성 문서(`tests/conftest.py`)에 실제 CLI를 돌린 결과입니다. 합성 문서이므로 한글(HWP)에서 열어 본 결과는 아닙니다.

**맞춤법 교정** — `proofread apply`

```diff
- [0] 첫 문단 본문이다.
+ [0] 첫 문단 본문입니다.
```

```
delta +1  p0  '본문이다' -> '본문입니다'
```

`Contents/section0.xml`만 바뀌고 `mimetype`·`version.xml`·`BinData/image1.png`는 바이트까지 같습니다. 엔트리 순서와 압축 방식도 그대로입니다.

**메모 제거** — `memo clear` 전후의 `verify` 출력

```diff
- {'wellformed': True, 'linesegarray': 1, 'memo_fields': 1, 'hyperlink_fields': 1, 'dup_equation_ids': []}
+ {'wellformed': True, 'linesegarray': 0, 'memo_fields': 0, 'hyperlink_fields': 1, 'dup_equation_ids': []}
```

메모와 줄 캐시만 사라지고 본문과 하이퍼링크는 남습니다.

**안전 실패** — 잘못된 요청은 파일을 만들지 않고 멈춥니다.

| 요청 | 결과 |
|------|------|
| 문단에 없는 문구로 교정 | `error: anchor not unique in paragraph 1 (count=0)`, 종료 코드 2, 출력 파일 없음 |
| 입력과 같은 경로로 저장 | `error: out_path must differ from original_path`, 종료 코드 2, 원본 해시 동일 |
| 없는 그림 슬롯 교체 | `error: no such entry in archive`, 종료 코드 2, 출력 파일 없음 |

---

## 🧭 활용 예시

실제 사용 후기가 아니라, CLI로 확인한 기능으로 구성한 예시입니다.

- **검토 메모를 지우고 제출본 만들기** — "메모 다 지우고 v2로 저장해줘" → 메모를 제거한 새 파일 저장 → `verify`로 메모 수 0 확인 → 한글에서 직접 확인
- **맞춤법을 고쳐 새 버전으로 저장하기** — "맞춤법 고쳐줘" → 문단별 교정안과 글자수 변화를 `--check`로 미리 확인 → 새 파일에 적용
- **문서 안의 그림만 교체하기** — "image1을 이 PNG로 바꿔줘" → 해당 슬롯의 PNG만 교체 → 새 그림과 기존 그림 영역의 종횡비를 출력해 비교

---

## 🛡 안전 보장

CLI가 강제하는 규칙입니다. 명령마다 적용 범위가 다르면 표에 함께 적었습니다.

| 규칙 | 설명 |
|------|------|
| 원본 in-place 금지 | 항상 새 파일(`-o`)로 저장. 출력 경로가 입력과 같으면 거부 |
| 구조 복제 재포장 | `mimetype` 최초 · STORED 압축 · 디렉터리 엔트리 0. 셸 `zip` 미사용 |
| linesegarray 제거 | `memo clear`·`edit`·`proofread apply`·`equation clone`에서 오래된 줄 캐시를 모두 삭제 → 한글이 레이아웃을 다시 계산하도록 함 |
| well-formed 검증 | 위 네 명령은 저장 전에 XML 유효성 검사. `repackage`·`figure swap`은 교체 대상이 아카이브에 없으면 거부하고, 교체하는 XML·HPF 엔트리를 검사 |
| 유일 앵커 | `edit`·`proofread apply`·`equation clone`은 앵커가 정확히 한 번 일치할 때만 적용. proofread는 문단 내 유일 + 단일 `<hp:t>` 런 강제 |
| 본문 텍스트 좌표계 | `edit`·`proofread apply`·`equation clone`은 메모·수식을 제외한 본문 `<hp:t>` 안에서만 앵커를 찾음. `edit`·`proofread apply`는 새 문구를 이스케이프해 마크업이 그대로 들어가지 않음 |

---

## 🗂 저장소 구성

```
hwpx-toolkit/
├── skills/hwpx-edit/
│   ├── SKILL.md                모델이 로드하는 스킬 정의(트리거·가이드)
│   ├── scripts/
│   │   ├── hwpx.py             통합 CLI (extract·memo·edit·proofread·figure·equation·verify·repackage)
│   │   └── _hwpxlib.py         stdlib 전용 코어 라이브러리
│   └── references/
│       ├── hwpx-internals.md   OWPML/HWPX 내부 구조 노트
│       └── workflows.md        작업별 레시피(맞춤법·메모·그림·수식·가이드 플로우)
├── tests/                      pytest(단위 + CLI E2E)
├── .github/workflows/test.yml  CI(OS·Python 조합별 pytest)
├── docs/superpowers/           설계(spec)·구현 계획(plan) 문서
├── .claude-plugin/             Claude Code 플러그인 매니페스트(plugin/marketplace)
├── codex/install.md            Codex 설치 안내
└── README.md · README.en.md · LICENSE · AGENTS.md · CLAUDE.md
```

런타임은 **순수 Python 3.9+ 표준 라이브러리**만 씁니다(서드파티 의존성 0, 외부 발송·네트워크 없음). pytest는 테스트 전용입니다.

---

## 🧰 CLI 서브커맨드

스킬이 내부에서 쓰는 CLI이며, 자동화·디버깅용으로 직접 실행할 수도 있습니다. 모든 쓰기 명령은 `-o` 새 파일로 저장합니다.

| 명령 | 역할 | 비고 |
|------|------|------|
| `extract FILE [--paragraphs\|--memos\|--equations]` | 본문 문단 · 메모 · 수식 스크립트 읽기 | 문단은 `[0] …` 번호로 출력 |
| `memo clear FILE -o OUT` | 검토 메모 전체 제거 | 본문·하이퍼링크 보존 |
| `edit FILE -o OUT --replace "old<TAB>new" [--check]` | 유일 앵커 치환 + 글자수 델타 | `--check`로 미리보기 |
| `proofread apply FILE -o OUT --from c.json [--check]` | 문단 스코프 맞춤법·문장 교정 | `c.json` = `[{"p":3,"old":"됬다","new":"됐다"}]` |
| `figure swap FILE -o OUT --slot imageN --png P` | 내장 PNG 교체 | 종횡비 참고 출력 |
| `equation clone FILE -o OUT --template "..." --anchor "..."` | 첨자 수식 복원 | 새 id 자동 부여 |
| `verify FILE` | 구조 검증 게이트 | wellformed·메모/수식 수 리포트 |
| `repackage --original F -o OUT --replace arc=path` | (저수준) 아카이브 엔트리로 재포장 | 구조 복제 |

---

## 🔄 맞춤법 교정 흐름 (proofread)

```
extract --paragraphs            문단 번호 확인
        ↓
모델이 오류 식별  →  corrections.json  [{ "p", "old", "new" }, ...]
        ↓
proofread apply --check         문단 스코프 검증 + 글자수 델타 미리보기(파일 미작성)
        ↓
proofread apply                 본문 <hp:t> 스팬만 splice · new만 XML 이스케이프
        ↓
strip linesegarray → well-formed 검증 → 구조 복제 재포장 → 새 파일
        ↓
verify → HWP로 열어 레이아웃 확인
```

`old`가 문단 안에서 유일하지 않거나 여러 `<hp:t>` 런에 걸치면 오류로 **안전하게 멈춥니다** → 더 짧은 단어 단위 앵커로 재시도. 자세한 설계는 `docs/superpowers/specs/2026-08-18-proofread-and-guided-flow-design.md` 참고.

---

## 🚀 설치

### Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-toolkit
```

### Codex

[`codex/install.md`](codex/install.md) 참고. Codex에서도 같은 `hwpx-edit` 스킬을 대화로 동일하게 사용합니다.

### 직접 실행(선택)

```bash
python3 skills/hwpx-edit/scripts/hwpx.py extract 논문.hwpx --paragraphs
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o 논문_v2.hwpx --from corrections.json --check
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply 논문.hwpx -o 논문_v2.hwpx --from corrections.json
python3 skills/hwpx-edit/scripts/hwpx.py verify 논문_v2.hwpx
```

---

## 🧪 테스트

프로젝트 venv로 전체 테스트를 실행합니다(macOS 시스템 파이썬은 외부 관리(PEP 668)라 pytest 직접 설치가 막혀 있어, `.venv/`가 정본입니다).

```bash
python3 -m venv .venv && .venv/bin/pip install pytest   # 최초 1회
.venv/bin/pytest -v                                      # 전부 통과해야 함
```

런타임은 Python 3.9+ stdlib만 필요하고, 테스트만 pytest에 의존합니다.

| CI | 범위 |
|----|------|
| 검증하는 것 | Ubuntu·macOS·Windows × Python 3.9·최신 3.x에서 pytest 실행. 픽스처는 테스트가 직접 만든 합성 `.hwpx`이며, CP949·CP1252 출력 환경의 CLI 동작도 포함 |
| 검증하지 못하는 것 | 한글(HWP)에서 실제로 열리는지, 레이아웃, 실제 문서와의 호환성 |

---

## ⚠️ 하지 않는 것 · 주의

- 새 문서 저작, PDF·docx·pptx 등 **다른 포맷 변환** — 이 도구의 용도가 아님
- 원본 파일 **덮어쓰기** — 항상 새 버전으로 저장
- 수식(`<hp:equation>`)·`&gt;` 이스케이프 구간을 **앵커로 사용** — 금지(모델 가이드)
- 여러 `<hp:t>` 런에 걸치는 앵커 — 미지원(안전 실패 후 재시도)
- `Contents/section0.xml` 밖의 본문 — 읽기·편집 모두 첫 섹션만 처리하므로 `section1.xml` 이후가 있는 문서는 주의
- 편집 후 레이아웃은 환경이 렌더링하지 못하므로, **한글(HWP)로 직접 열어 확인** 필요

---

## 📚 문서

| 파일 | 내용 |
|------|------|
| `skills/hwpx-edit/SKILL.md` | 스킬 정의 · 트리거 · 모델 가이드 |
| `skills/hwpx-edit/references/hwpx-internals.md` | OWPML/HWPX 내부 구조 노트 |
| `skills/hwpx-edit/references/workflows.md` | 작업별 레시피(맞춤법·메모·그림·수식·가이드 플로우) |
| `docs/superpowers/specs/` | 설계 문서(리뷰 반영본) |
| `docs/superpowers/plans/` | TDD 구현 계획 |
| `AGENTS.md` | 프로젝트 규칙 · 안전 불변식 |
| `README.en.md` | English README |

---

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE)로 배포됩니다.
