---
name: hwpx-edit
description: Use for ANY task that edits an existing .hwpx (한글) file and saves it back as .hwpx — the safe way to modify .hwpx without corrupting it. Covers reading body/memo/equation text, removing memos, adjusting paragraph length by exact character count, swapping embedded figures, and restoring subscript equations. Do NOT use for PDF/format conversion or authoring a new document.
---

# Editing HWPX safely

HWPX is a ZIP of OWPML XML. Two traps: HWP refuses to open a carelessly rebuilt
zip, and stale line caches make text overlap. This skill's CLI handles both.

## The CLI
Run: `python3 <this skill>/scripts/hwpx.py <subcommand>`
(On Claude Code the skill dir is `${CLAUDE_PLUGIN_ROOT}/skills/hwpx-edit`.)

- `extract FILE [--paragraphs|--memos|--equations]` — read content.
- `memo clear FILE -o OUT` — remove all memos, keep body + hyperlinks.
- `edit FILE -o OUT --replace "old<TAB>new" [...] [--check]` — unique-anchor
  replacements; prints each char delta. Use `--check` first.
- `figure swap FILE -o OUT --slot imageN --png P` — replace embedded PNG.
- `equation clone FILE -o OUT --template "device _{key}" --anchor "PLAIN"` —
  restore a subscript term as an equation object.
- `verify FILE` — structural gate.

## Non-negotiable rules
1. Never edit the original in place — always `-o` a new version (bump the ver number).
2. The CLI repackages by structure-clone; never shell `zip`.
3. Text changes strip all linesegarray (CLI does this) so HWP recomputes layout.
4. `edit` anchors MUST be unique. Choose anchors in **pure Korean** runs — never
   spanning an `<hp:equation>` or containing `&gt;` (the XML escape for `>`).
5. You (the model) craft the replacement text: meaning-preserving, hitting the
   requested character delta; the CLI reports the delta so you can check.

## Limitation
The environment cannot render HWPX. After editing, tell the author to open the
file in HWP and eyeball layout (a benign "변조 가능성" warning may appear).
See references/hwpx-internals.md and references/workflows.md.
