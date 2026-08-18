# hwpx-toolkit

한글(HWPX) 문서를 **손상 없이 읽고 편집**하는 워크플로우를 **Claude Code + Codex 플러그인**으로 패키징한 스킬 레포. 공개(MIT).

## 정본/구조
- 공용 코어 = `skills/hwpx-edit/`(SKILL.md + `scripts/hwpx.py` 통합 CLI + references). 두 플랫폼이 같은 SKILL.md를 로드한다.
- 플랫폼 차이는 **설치 매니페스트뿐**: Claude Code = `.claude-plugin/`, Codex = `codex/install.md`.
- 설계 문서: `docs/superpowers/specs/`. 구현 계획: `docs/superpowers/plans/`.

## 항상 지킬 것 (안전 불변식)
- 원본 hwpx를 **절대 in-place 수정 금지** — 항상 새 파일로.
- 재포장은 **구조 복제**(mimetype 최초·STORED·디렉터리 엔트리 0)로만. 셸 `zip` 금지.
- 텍스트 변경 시 **linesegarray 전부 strip**.
- 쓰기 전 **well-formed 검증**. `edit`의 old 앵커는 **유일성 강제**.
- 수식(HancomEQN)·`&gt;` 이스케이프 구간은 앵커로 쓰지 않는다.

## 역할 분담
- 스크립트(결정론): 재포장·추출·유일성검사·글자수 델타·이미지 교체·수식 복제·strip·검증.
- 모델(판단, SKILL.md 안내): 의미 보존 문구 작성, 유일 앵커 선택, 메모/본문 구분, 렌더(PDF) 읽고 widow 파악.
