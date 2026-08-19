<!-- 한국어: [README.md](README.md) | English: this file -->

# hwpx-toolkit

Safely read and edit 한글(HWPX) files from the command line — without corrupting the ZIP structure or triggering text overlap. Packaged as a Claude Code plugin and Codex skill.

## What it is

HWPX is a ZIP container of OWPML XML. Two pitfalls make naive editing dangerous: HWP refuses to open a carelessly rebuilt ZIP, and stale line-position caches cause text to render on top of itself. This toolkit's CLI (`hwpx.py`) handles both automatically.

Supported operations:
- **extract** — read body paragraphs, memos, or equation scripts
- **memo clear** — remove all reviewer memos, keep body and hyperlinks
- **edit** — replace text by unique anchor, with per-replacement char-delta reporting
- **proofread apply** — paragraph-scoped spelling/wording corrections from a JSON file (the model finds errors, the script applies them safely)
- **figure swap** — replace an embedded PNG by slot name
- **equation clone** — restore a subscript term as an `<hp:equation>` object
- **verify** — structural gate before handing off the file
- **repackage** — low-level: rebuild ZIP from a modified archive entry

There is also a **guided task-selection flow** (skill-level): pre-scan the document, present a multi-select checklist of operations, then chain the chosen operations into a single pipeline.

## Safety guarantees

1. **Never in-place** — always write to a new file via `-o`. The original is never touched.
2. **Structure-clone repackaging** — `mimetype` entry first, STORED compression, no directory entries. Shell `zip` is never used.
3. **linesegarray stripped** — all stale line caches are removed on every text change so HWP recomputes clean layout on open.
4. **Well-formed check** — XML is validated before the output file is written.
5. **Unique anchors** — `edit` refuses a replacement whose anchor matches more than once; `proofread` requires each `old` to be unique within its paragraph and inside a single `<hp:t>` run.
6. **Text-coordinate only** — `proofread` matches and replaces only inside body `<hp:t>` text; only the replacement is XML-escaped, so surrounding entities are preserved byte-for-byte and markup can never be injected. Anchors never span an `<hp:equation>` or a `&gt;` escape.

## Install — Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-edit
```

After install, use the `hwpx-edit` skill for any `.hwpx` editing task.

## Install — Codex

See [`codex/install.md`](codex/install.md).

## Usage example

**Clear memos from a draft:**

```bash
python3 skills/hwpx-edit/scripts/hwpx.py memo clear draft.hwpx -o draft_clean.hwpx
```

**Spelling/wording corrections (proofread):**

```bash
# 1) read numbered paragraphs
python3 skills/hwpx-edit/scripts/hwpx.py extract paper.hwpx --paragraphs

# 2) write corrections.json — p is the paragraph index from step 1
#    [{"p": 3, "old": "됬다", "new": "됐다"}]

# 3) preview char deltas (writes nothing)
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o /tmp/preview.hwpx --from corrections.json --check

# 4) apply
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json
```

## For contributors

Run the full test suite with the project venv:

```bash
.venv/bin/pytest -v
```

(The project venv at `.venv/` is the canonical environment because macOS system Python is externally managed (PEP 668). Recreate it with `python3 -m venv .venv && .venv/bin/pip install pytest` if missing.)

All 43 tests must pass. Tests are in `tests/` and require only Python 3.9+ stdlib plus pytest.

## License

MIT — see [LICENSE](LICENSE).
