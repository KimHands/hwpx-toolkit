# hwpx-toolkit — 설계 문서

작성일: 2026-08-18
상태: 승인됨 (구현 계획 대기)

## 1. 목적

한글(HWPX) 문서를 **손상 없이 읽고 편집**하는 워크플로우를 **Claude Code와 Codex 양쪽에서 쓰는 플러그인/스킬 레포**로 패키징한다. 2026 국가암호공모전 논문 작업 세션에서 반복적으로 발전시킨 기법(메모 제거, 문단 글자수 조정, 수식 읽기·복제, 그림 교체 등)을 재사용 가능한 도구로 굳히는 것이 목표다.

핵심 원칙: **결정론적·검증 가능한 부분은 스크립트**가, **언어·판단이 필요한 부분은 모델**이 맡는다. 이 분담 덕에 Claude Code·Codex 어느 쪽이든 "모델이 스크립트를 호출"하는 동일 방식으로 동작한다.

## 2. 대상 플랫폼

- **Claude Code**: `.claude-plugin/plugin.json` + `marketplace.json`으로 배포/설치. `skills/`는 자동 발견.
- **Codex**: SKILL.md를 네이티브 로드하므로 **같은 `skills/hwpx-edit/`를 재사용**. `codex/install.md`가 설치 방법 안내.
- 두 플랫폼이 **하나의 공용 코어(스킬 폴더)** 를 공유하고, 차이는 설치 매니페스트뿐이다.

## 3. 레포 구조

```
hwpx-toolkit/                      # 레포 루트 = Claude Code 플러그인
├── README.md                     # 두 플랫폼 설치법·사용 예·안전 규칙
├── LICENSE                       # MIT
├── .claude-plugin/
│   ├── plugin.json               # Claude Code 플러그인 매니페스트
│   └── marketplace.json          # /plugin marketplace add <owner>/hwpx-toolkit
├── skills/hwpx-edit/             # 공용 코어 (두 플랫폼 공유)
│   ├── SKILL.md                  # 워크플로우 진입점 + 안전 규칙 + 각 커맨드 사용 시점
│   ├── scripts/
│   │   ├── hwpx.py               # 통합 CLI (서브커맨드)
│   │   └── _hwpxlib.py           # 공용 헬퍼(zip 구조복제·XML·텍스트추출)
│   └── references/
│       ├── hwpx-internals.md     # OWPML XML 사실 (현행 hwpx-edit에서 이관)
│       └── workflows.md          # widow·메모·그림·수식·인용 레시피
├── codex/install.md              # Codex 설치 가이드
└── tests/
    ├── fixtures/sample.hwpx      # 최소 픽스처(메모1·하이퍼링크1·수식1·문단 몇 개)
    └── test_hwpx.py              # 라운드트립·안전성 회귀 테스트
```

## 4. 통합 CLI (`hwpx.py`) — 공용 코어

모든 쓰기 커맨드는 **원본 보존 + 구조복제 재포장 + linesegarray strip + well-formed 검증**을 내장한다.

| 서브커맨드 | 동작 (결정론·검증) |
|---|---|
| `extract <f> [--paragraphs\|--memos\|--equations\|--refs]` | 본문/메모/수식 스크립트/참고문헌을 텍스트로 덤프(문단 인덱스 포함). 기본은 본문 plain text. |
| `memo clear <f> -o <out>` | 메모(주석) 필드 전부 제거. **앵커 본문·하이퍼링크 필드 보존.** linesegarray strip → 재포장. |
| `edit <f> -o <out> --replace "old⇥new" … [--check]` | 각 old의 **유일성 강제**(아니면 오류+count). 적용 후 **글자수 델타 출력.** strip → well-formed 검증 → 재포장. `--check`는 드라이런(유일성+델타만). |
| `figure swap <f> -o <out> --slot imageN --png <p>` | BinData/imageN.png 교체. **imgDim(HWPUNIT) 종횡비 vs 새 PNG 종횡비 대조**, 임계 초과 시 경고. 재포장. |
| `equation clone <f> -o <out> --template "device _{key}" --anchor "plain::mode"` | 기존 수식 객체를 복제(새 unique id)해 앵커 지점에 삽입. 아래첨자 평문 복원용(희소). |
| `verify <f>` | well-formed · linesegarray 수 · 메모/하이퍼링크 필드 수 · 수식 id 중복 게이트. |
| `repackage --original <f> --replace "path=file" … -o <out>` | 저수준 구조복제 재포장(다른 커맨드가 내부 사용, 고급용 노출). |

`edit`가 **widow ±N글자 조정·표기 일관성·오타 수정**을 전부 담당한다.

### 델타 규약
`--replace "old⇥new"`에서 구분자는 탭 또는 명시적 구분(예: `--replace-old`/`--replace-new` 페어). `edit`는 각 교체의 `len(new)-len(old)`(공백 포함 유니코드 코드포인트 기준)를 출력해, 요청 글자수와 대조할 수 있게 한다.

## 5. 스크립트 ↔ 모델 역할 분담

- **스크립트(결정론)**: 재포장, 추출, 앵커 유일성 검사, 글자수 카운트, 이미지 교체, 수식 복제, linesegarray strip, well-formed 검증.
- **모델(판단, SKILL.md가 안내)**: 목표 글자수에 맞는 **의미 보존 문구 작성**, 수식·`&gt;` 안 겹치는 **유일 앵커 선택**, 메모/본문 구분, PDF가 있으면 **렌더 읽고 widow 위치 파악**.

## 6. 안전 불변식 (모든 쓰기 커맨드)

1. 원본 파일 **절대 in-place 수정 금지** — 항상 `-o <out>` 새 파일.
2. 재포장은 **원본 zip infolist 구조 복제**(mimetype 최초·STORED·압축방식·엔트리 순서 보존, 디렉터리 엔트리 0). 셸 `zip` 금지.
3. 텍스트 변경 시 **linesegarray 전부 제거**(HWP가 재계산 → 겹침 방지).
4. 쓰기 전 `xml.dom.minidom.parseString`으로 **well-formed 검증**.
5. `edit`의 old 앵커는 **유일(count==1)** 이어야 하며, 아니면 오류로 중단.
6. 수식(HancomEQN `<hp:script>`)·`&gt;` 이스케이프가 포함된 구간은 앵커로 쓰지 않는다(모델 책임, SKILL.md 명시).

## 7. 패키징

### Claude Code
- `.claude-plugin/plugin.json`: name·version·description·author.
- 루트 `marketplace.json`: `/plugin marketplace add <owner>/hwpx-toolkit` → `/plugin install`.
- SKILL.md는 스크립트를 `${CLAUDE_PLUGIN_ROOT}/skills/hwpx-edit/scripts/hwpx.py`로 호출.

### Codex
- Codex는 SKILL.md 네이티브 로드 → 같은 `skills/hwpx-edit/` 재사용.
- `codex/install.md`: 레포 클론 후 `skills/hwpx-edit/`를 Codex 스킬 경로에 복사/심링크, 또는 AGENTS.md에서 참조.
- **이식성**: SKILL.md가 CLI를 "이 스킬 폴더 기준 `scripts/hwpx.py`"로 지칭 → 설치 위치·플랫폼 무관.

## 8. 테스트 (안전성 회귀)

pytest + 최소 픽스처 `sample.hwpx`:
1. 재포장 구조 동일성(mimetype 최초·STORED·디렉터리 엔트리 0·infolist 순서).
2. `extract` 문단/메모/수식 정확성.
3. `memo clear`가 본문 앵커·하이퍼링크 보존 + 메모 제거.
4. `edit`: 비유일 old→오류, 유일→적용+델타 정확, 이후 well-formed.
5. `figure swap`: 이미지 교체 + 종횡비 경고 로직.
6. `verify`: 손상/수식 id 중복 탐지.

(선택) GitHub Actions로 pytest CI.

## 9. 배포·이름·라이선스

- **공개 GitHub 레포.**
- 레포명 **`hwpx-toolkit`**, 스킬명 `hwpx-edit`.
- 라이선스 **MIT**.
- README: 두 플랫폼 설치법·사용 예·안전 규칙. 현행 `hwpx-edit`의 SKILL.md·hwpx-internals.md 이관, 세션 레시피를 `workflows.md`로 정리, 스크립트는 `hwpx.py`로 통합.

## 10. 비목표 (YAGNI)

- GUI/웹 인터페이스 없음.
- PDF 렌더링은 스크립트가 하지 않음(사용자가 HWP로 렌더, 모델이 읽음).
- .hwp(구형 바이너리)·docx/pptx 변환은 범위 밖.
- 조판 자간 미세조정 자동화는 범위 밖(모델+사용자 렌더 루프).
