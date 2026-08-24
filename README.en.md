<!-- 한국어: [README.md](README.md) | English: this file -->

<div align="center">

# 📝 hwpx-toolkit

**Safely read and edit 한글(HWPX) files — a Claude Code · Codex skill**

*.hwpx is a fragile ZIP structure: save it carelessly and HWP won't open the file.*
*This skill repackages by cloning the structure and prevents text overlap, so you edit safely — just by talking.*

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)
![deps](https://img.shields.io/badge/deps-stdlib_only-success)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-8A63D2)
![Codex](https://img.shields.io/badge/Codex-skill-000000)
![Tests](https://img.shields.io/badge/tests-43_passing-success)
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
swap chapters 3 and 4 and renumber the references in appearance order
```

You can also pick it from the slash menu — press `/` and type `hwpx`. The name depends on install method: as a plugin it is **`hwpx-toolkit:hwpx-edit`**; as a personal skill (`~/.claude/skills/hwpx-edit/`) it shows as `/hwpx-edit`.

Claude then reads the body/paragraphs, drafts the edits, applies them safely at paragraph scope, verifies, and **saves to a new file**. When done it tells you to open the file in HWP to eyeball the layout (a benign "변조 가능성" warning may appear).

---

## 🛡 Safety guarantees

However the edit is triggered, these always hold.

| Rule | What it means |
|------|---------------|
| Never in-place | Always writes a new file (`-o`); the original is never modified |
| Structure-clone repackaging | `mimetype` first · STORED compression · no directory entries. Shell `zip` is never used |
| linesegarray stripped | Stale line caches removed on every text change → HWP recomputes layout (no text overlap) |
| Well-formed check | XML validated before the output is written |
| Unique anchors | A replacement matching more than once is refused; proofread requires uniqueness within a paragraph and a single `<hp:t>` run |
| Text-coordinate only | Matches/replaces only inside body `<hp:t>`; only the replacement is escaped → entities preserved byte-for-byte, no markup injection |

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
├── tests/                      pytest — 43 (unit + CLI E2E)
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
.venv/bin/pytest -v                                      # all 43 must pass
```

The runtime needs only Python 3.9+ stdlib; only the tests depend on pytest.

---

## ⚠️ Out of scope · caveats

- Authoring new documents, or converting to PDF/docx/pptx — not what this tool does
- Overwriting the original — always saves a new version
- Using an `<hp:equation>` or a `&gt;` escape as an anchor — forbidden (model guidance)
- Anchors spanning multiple `<hp:t>` runs — unsupported (safe fail, then retry)
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
