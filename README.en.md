<!-- 한국어: [README.md](README.md) | English: this file -->

<div align="center">

# 📝 hwpx-toolkit

**Safely read and edit 한글(HWPX) files — a Claude Code · Codex skill**

*.hwpx is a fragile ZIP structure: save it carelessly and HWP won't open the file.*
*This skill repackages by cloning the structure and clears stale line caches, so you can run the edit just by talking.*

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![deps](https://img.shields.io/badge/deps-stdlib_only-success)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8A63D2)
![Codex](https://img.shields.io/badge/Codex-skill-000000)
[![tests](https://github.com/KimHands/hwpx-toolkit/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/KimHands/hwpx-toolkit/actions/workflows/test.yml)
![License](https://img.shields.io/badge/License-MIT-black)

</div>

> **Scope positioning** — hwpx-toolkit does **not** author new documents or convert to PDF/docx.
> It **edits an existing `.hwpx` safely and saves a new version**. The original is never touched.

---

## ✨ Features

- **Spelling/wording proofread** — paragraph-scoped corrections on body text only; surrounding entities and markup are preserved byte-for-byte
- **Clear reviewer memos** — remove all memos while keeping body text and hyperlinks
- **Char-delta edit** — replace text by unique anchor and report the exact character delta (widow/orphan fixes)
- **Figure swap · equation clone** — replace an embedded PNG by slot name, restore a subscript term as an `<hp:equation>` object
- **Read / verify** — extract body, memos, equations; structural gate before handing off
- **Guided task-selection flow** — pick operations from a checklist and chain them in one pass
- **Scripts = deterministic, model = judgment** — repackage/verify/char-deltas by scripts; error-finding and wording by the model

---

## 💬 Usage — Claude Code

Once installed, you **don't run the CLI yourself.** Just describe the task in the chat (natural language) and the `hwpx-edit` skill activates — the most reliable way.

```
fix the typos in this paper.hwpx
remove all the memos and save as v2
change this sentence as follows and tell me the character delta
```

You can also pick it from the slash menu — press `/` and type `hwpx`. The name depends on install method: as a plugin it is **`hwpx-toolkit:hwpx-edit`**; as a personal skill (`~/.claude/skills/hwpx-edit/`) it shows as `/hwpx-edit`.

Claude then reads the body/paragraphs, drafts the edits, applies them safely at paragraph scope, verifies, and **saves to a new file**. When done it tells you to open the file in HWP to eyeball the layout (a benign "변조 가능성" warning may appear).

---

## 🔍 Before and after

These are real CLI results on the synthetic test document (`tests/conftest.py`). Because it is synthetic, it has not been opened in HWP.

**Proofread** — `proofread apply`

```diff
- [0] 첫 문단 본문이다.
+ [0] 첫 문단 본문입니다.
```

```
delta +1  p0  '본문이다' -> '본문입니다'
```

Only `Contents/section0.xml` changes; `mimetype`, `version.xml`, and `BinData/image1.png` stay byte-identical. Entry order and compression methods are unchanged too.

**Memo removal** — `verify` output before and after `memo clear`

```diff
- {'wellformed': True, 'linesegarray': 1, 'memo_fields': 1, 'hyperlink_fields': 1, 'dup_equation_ids': []}
+ {'wellformed': True, 'linesegarray': 0, 'memo_fields': 0, 'hyperlink_fields': 1, 'dup_equation_ids': []}
```

Only the memo and line cache go away; body text and the hyperlink remain.

**Safe failure** — an invalid request stops without producing a file.

| Request | Result |
|---------|--------|
| Correct text that isn't in the paragraph | `error: anchor not unique in paragraph 1 (count=0)`, exit code 2, no output file |
| Save to the input path | `ValueError: out_path must differ from original_path`, original hash unchanged |

---

## 🧭 Example scenarios

These are illustrations built from features confirmed with the CLI, not reports from real use.

- **Clear review memos for a submission copy** — "remove all the memos and save as v2" → saves a new file without memos → `verify` shows zero memos → check it yourself in HWP
- **Proofread into a new version** — "fix the typos" → preview per-paragraph corrections and character deltas with `--check` → apply to a new file
- **Swap one embedded figure** — "replace image1 with this PNG" → replaces only that PNG slot → prints aspect ratios for the new PNG and existing image areas to compare

---

## 🛡 Safety guarantees

The CLI enforces these rules. Where the scope differs by command, the table says so.

| Rule | What it means |
|------|---------------|
| Never in-place | Always writes a new file (`-o`); refuses an output path equal to the input |
| Structure-clone repackaging | `mimetype` first · STORED compression · no directory entries. Shell `zip` is never used |
| linesegarray stripped | `memo clear`, `edit`, `proofread apply`, and `equation clone` remove all stale line caches → HWP is left to recompute layout |
| Well-formed check | Those four commands validate XML before writing. Low-level `repackage` does not, so check its output with `verify` |
| Unique anchors | `edit`, `proofread apply`, and `equation clone` apply only when the anchor matches exactly once; proofread requires uniqueness within a paragraph and a single `<hp:t>` run |
| Text-coordinate (`proofread`) | Matches/replaces only inside body `<hp:t>`; only the replacement is escaped → entities preserved byte-for-byte, no markup injection |

> `edit` replaces raw section XML. It can match equation scripts and does not escape the new text, so use `proofread` for body-text corrections.

---

## 🗂 Repository layout

```
hwpx-toolkit/
├── skills/hwpx-edit/
│   ├── SKILL.md                skill definition the model loads (triggers, guidance)
│   ├── scripts/
│   │   ├── hwpx.py             unified CLI (extract·memo·edit·proofread·figure·equation·verify·repackage)
│   │   └── _hwpxlib.py         stdlib-only core library
│   └── references/
│       ├── hwpx-internals.md   OWPML/HWPX internals notes
│       └── workflows.md        per-task recipes (proofread, memo, figure, equation, guided flow)
├── tests/                      pytest (unit + CLI E2E)
├── .github/workflows/test.yml  CI (pytest across OS and Python versions)
├── docs/superpowers/           design specs and implementation plans
├── .claude-plugin/             Claude Code plugin manifests (plugin/marketplace)
├── codex/install.md            Codex install guide
└── README.md · README.en.md · LICENSE · AGENTS.md · CLAUDE.md
```

The runtime uses **pure Python 3.9+ standard library** only (zero third-party deps, no network/outbound). pytest is a test-only dependency.

---

## 🧰 CLI subcommands

The CLI the skill uses under the hood — also runnable directly for automation/debugging. Every write command saves to a new `-o` file.

| Command | Purpose | Notes |
|---------|---------|-------|
| `extract FILE [--paragraphs\|--memos\|--equations]` | read body paragraphs · memos · equation scripts | paragraphs print as `[0] …` |
| `memo clear FILE -o OUT` | remove all reviewer memos | keeps body + hyperlinks |
| `edit FILE -o OUT --replace "old<TAB>new" [--check]` | unique-anchor replace + char delta | `--check` to preview |
| `proofread apply FILE -o OUT --from c.json [--check]` | paragraph-scoped spelling/wording | `c.json` = `[{"p":3,"old":"됬다","new":"됐다"}]` |
| `figure swap FILE -o OUT --slot imageN --png P` | replace embedded PNG | prints aspect ratios |
| `equation clone FILE -o OUT --template "..." --anchor "..."` | restore a subscript equation | assigns a fresh id |
| `verify FILE` | structural gate | reports wellformed · memo/equation counts |
| `repackage --original F -o OUT --replace arc=path` | (low-level) rebuild from an archive entry | structure-clone |

---

## 🔄 Proofread flow

```
extract --paragraphs            read numbered paragraphs
        ↓
model finds errors  →  corrections.json  [{ "p", "old", "new" }, ...]
        ↓
proofread apply --check         paragraph-scoped validation + char-delta preview (no file)
        ↓
proofread apply                 splice only the matched <hp:t> span · escape only `new`
        ↓
strip linesegarray → well-formed check → structure-clone repackage → new file
        ↓
verify → open in HWP to check layout
```

If `old` is not unique within its paragraph, or spans multiple `<hp:t>` runs, it **fails safely** → retry with a shorter word-level anchor. See `docs/superpowers/specs/2026-08-18-proofread-and-guided-flow-design.md`.

---

## 🚀 Install

### Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-toolkit
```

### Codex

See [`codex/install.md`](codex/install.md). Codex surfaces the same `hwpx-edit` skill; use it conversationally the same way.

### Run directly (optional)

```bash
python3 skills/hwpx-edit/scripts/hwpx.py extract paper.hwpx --paragraphs
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json --check
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json
python3 skills/hwpx-edit/scripts/hwpx.py verify paper_v2.hwpx
```

---

## 🧪 Tests

Run the full suite with the project venv (macOS system Python is externally managed, PEP 668, so `.venv/` is canonical).

```bash
python3 -m venv .venv && .venv/bin/pip install pytest   # first time
.venv/bin/pytest -v                                      # all must pass
```

The runtime needs only Python 3.9+ stdlib; only the tests depend on pytest.

| CI | Scope |
|----|-------|
| Covers | pytest on Ubuntu, macOS, and Windows × Python 3.9 and latest 3.x. Fixtures are synthetic `.hwpx` files built by the tests; CLI behavior under CP949 and CP1252 output is included |
| Does not cover | Whether files actually open in HWP, layout, or compatibility with real-world documents |

---

## ⚠️ Out of scope · caveats

- Authoring new documents, or converting to PDF/docx/pptx — not what this tool does
- Overwriting the original — always saves a new version
- Using an `<hp:equation>` or a `&gt;` escape as an anchor — forbidden (model guidance)
- Anchors spanning multiple `<hp:t>` runs — unsupported (safe fail, then retry)
- Body text outside `Contents/section0.xml` — reads and edits cover only the first section, so take care with documents that have `section1.xml` or later
- The environment can't render HWPX, so **open the file in HWP** to confirm layout after editing

---

## 📚 Docs

| File | Contents |
|------|----------|
| `skills/hwpx-edit/SKILL.md` | skill definition · triggers · model guidance |
| `skills/hwpx-edit/references/hwpx-internals.md` | OWPML/HWPX internals notes |
| `skills/hwpx-edit/references/workflows.md` | per-task recipes (proofread, memo, figure, equation, guided flow) |
| `docs/superpowers/specs/` | design docs (with review revisions) |
| `docs/superpowers/plans/` | TDD implementation plans |
| `AGENTS.md` | project rules · safety invariants |
| `README.md` | 한국어 README |

---

## 📄 License

Released under the [MIT License](LICENSE).
