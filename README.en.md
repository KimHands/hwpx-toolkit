<!-- 한국어: [README.md](README.md) | English: this file -->

# hwpx-toolkit

Safely read and edit 한글(HWPX) files — without corrupting the ZIP structure or triggering text overlap. Packaged as a Claude Code plugin and Codex skill. (MIT)

## What it is

HWPX is a ZIP container of OWPML XML. Two pitfalls make naive editing dangerous: HWP refuses to open a carelessly rebuilt ZIP, and stale line-position caches cause text to render on top of itself. This skill handles both automatically.

The split is deliberate — **the scripts do the deterministic work** (repackage, extract, uniqueness checks, char deltas, strip, verify) and **the model (Claude) does the language judgment** (finding errors, wording corrections, choosing anchors).

### What it can do

| Task | Description |
|---|---|
| Read body/memo/equation | extract body paragraphs, reviewer memos, or equation scripts |
| Clear memos | remove all reviewer memos, keep body and hyperlinks |
| Char-delta edit | replace text by unique anchor with per-replacement char-delta (widow/orphan fixes) |
| **Spelling/wording proofread** | apply paragraph-scoped corrections safely |
| Figure swap | replace an embedded PNG by slot name (aspect match) |
| Equation clone | restore a subscript term as an `<hp:equation>` object |
| Verify | structural gate before handing off the file |
| Guided flow | pick operations from a checklist and chain them in one pass |

## Usage — Claude Code (primary)

Once the plugin is installed you **don't run the CLI yourself.** Just describe the task in the Claude Code chat (natural language) and the `hwpx-edit` skill activates and runs the toolkit safely — this is the most reliable way.

Type things like:

```
fix the typos in this paper.hwpx
```
```
remove all the memos and save as v2
```
```
swap chapters 3 and 4 and renumber the references in appearance order
```

You can also pick it from the slash menu: press `/` and type `hwpx`. The exact name depends on how it was installed — **as a plugin it is namespaced, e.g. `hwpx-toolkit:hwpx-edit`**; as a personal skill (`~/.claude/skills/hwpx-edit/`) it shows as `/hwpx-edit`. (No need to memorize the string — just find it by typing `/hwpx`.)

Claude then reads the body/paragraphs, drafts the corrections/edits, applies them safely at paragraph scope, verifies, and **saves to a new file** — the original is never overwritten. When done it tells you to open the file in HWP to eyeball the layout (a benign "변조 가능성" warning may appear).

### Install — Claude Code

```
/plugin marketplace add KimHands/hwpx-toolkit
/plugin install hwpx-toolkit
```

### Install — Codex

See [`codex/install.md`](codex/install.md). Codex surfaces the same `hwpx-edit` skill; use it conversationally the same way.

## Safety guarantees

However the edit is triggered, these always hold:

1. **Never in-place** — always write to a new file. The original is never touched.
2. **Structure-clone repackaging** — `mimetype` entry first, STORED compression, no directory entries. Shell `zip` is never used.
3. **linesegarray stripped** — stale line caches removed on every text change so HWP recomputes clean layout.
4. **Well-formed check** — XML is validated before the output file is written.
5. **Unique anchors** — a replacement whose anchor matches more than once is refused; proofread requires each `old` to be unique within its paragraph and inside a single text run.
6. **Text-coordinate only** — proofread matches/replaces only inside body text and escapes only the replacement, so surrounding entities are preserved byte-for-byte and markup can never be injected. Anchors never span an `<hp:equation>` or a `&gt;` escape.

## Running the CLI directly (optional · automation/contributors)

The CLI the skill uses under the hood can also be run directly:

```bash
# read numbered paragraphs
python3 skills/hwpx-edit/scripts/hwpx.py extract paper.hwpx --paragraphs

# proofread: corrections.json = [{"p":3,"old":"됬다","new":"됐다"}]
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json --check  # preview
python3 skills/hwpx-edit/scripts/hwpx.py proofread apply paper.hwpx -o paper_v2.hwpx --from corrections.json          # apply

python3 skills/hwpx-edit/scripts/hwpx.py memo clear draft.hwpx -o draft_clean.hwpx
python3 skills/hwpx-edit/scripts/hwpx.py verify paper_v2.hwpx
```

Subcommands: `extract` · `memo clear` · `edit` · `proofread apply` · `figure swap` · `equation clone` · `verify` · `repackage`.

## For contributors

```bash
.venv/bin/pytest -v
```

The project venv at `.venv/` is the canonical test environment (macOS system Python is externally managed, PEP 668). Recreate with `python3 -m venv .venv && .venv/bin/pip install pytest` if missing. All 43 tests must pass; runtime is pure Python 3.9+ stdlib.

## License

MIT — see [LICENSE](LICENSE).
