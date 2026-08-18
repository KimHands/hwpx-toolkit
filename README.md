# hwpx-toolkit

Safely read and edit 한글(HWPX) files from the command line — without corrupting the ZIP structure or triggering text overlap. Packaged as a Claude Code plugin and Codex skill.

## What it is

HWPX is a ZIP container of OWPML XML. Two pitfalls make naive editing dangerous: HWP refuses to open a carelessly rebuilt ZIP, and stale line-position caches cause text to render on top of itself. This toolkit's CLI (`hwpx.py`) handles both automatically.

Supported operations:
- **extract** — read body paragraphs, memos, or equation scripts
- **memo clear** — remove all reviewer memos, keep body and hyperlinks
- **edit** — replace text by unique anchor, with per-replacement char-delta reporting
- **figure swap** — replace an embedded PNG by slot name
- **equation clone** — restore a subscript term as an `<hp:equation>` object
- **verify** — structural gate before handing off the file
- **repackage** — low-level: rebuild ZIP from a modified archive entry

## Safety guarantees

1. **Never in-place** — always write to a new file via `-o`. The original is never touched.
2. **Structure-clone repackaging** — `mimetype` entry first, STORED compression, no directory entries. Shell `zip` is never used.
3. **linesegarray stripped** — all stale line caches are removed on every text change so HWP recomputes clean layout on open.
4. **Well-formed check** — XML is validated before the output file is written.
5. **Unique anchors** — `edit` refuses to apply a replacement whose anchor matches more than once.
6. **No equation anchors** — anchors must be in plain Korean text runs, never spanning an `<hp:equation>` or a `&gt;` escape.

## Install — Claude Code

```
/plugin marketplace add KimJongGun/hwpx-toolkit
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

**Dry-run a widow fix (±3 chars) before applying:**

```bash
# Check the char delta without writing output
python3 skills/hwpx-edit/scripts/hwpx.py edit draft.hwpx -o /dev/null \
  --replace "논문의 특유한 구절이다	논문의 짧은 구절" --check

# Apply when the delta looks right
python3 skills/hwpx-edit/scripts/hwpx.py edit draft.hwpx -o draft_v2.hwpx \
  --replace "논문의 특유한 구절이다	논문의 짧은 구절"
```

Note: `--replace` takes `old<TAB>new` — a literal tab character separates old from new.

## For contributors

Run the full test suite with the project venv:

```bash
.venv/bin/pytest -v
```

(Standard `python -m pytest` also works if your active Python has pytest installed, but the project venv at `.venv/` is the canonical environment.)

All 24 tests must pass. Tests are in `tests/` and require only Python 3.9+ stdlib plus pytest.

## License

MIT — see [LICENSE](LICENSE).
