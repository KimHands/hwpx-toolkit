# Codex install — hwpx-edit

## Requirements

Python 3.9+ (stdlib only — no additional packages needed at runtime).

## Install

1. Clone the repo:

   ```bash
   git clone https://github.com/KimJongGun/hwpx-toolkit.git
   ```

2. Make the skill visible to Codex by copying or symlinking `skills/hwpx-edit/` into your Codex skills directory:

   **System-wide (all projects):**
   ```bash
   cp -r hwpx-toolkit/skills/hwpx-edit ~/.codex/skills/hwpx-edit
   # or symlink:
   ln -s "$(pwd)/hwpx-toolkit/skills/hwpx-edit" ~/.codex/skills/hwpx-edit
   ```

   **Project-local only:**
   ```bash
   mkdir -p .codex/skills
   cp -r hwpx-toolkit/skills/hwpx-edit .codex/skills/hwpx-edit
   # or symlink:
   ln -s "$(realpath hwpx-toolkit/skills/hwpx-edit)" .codex/skills/hwpx-edit
   ```

3. Codex will load `skills/hwpx-edit/SKILL.md` automatically when the skill directory is present.

## Invoking the CLI

The CLI is invoked directly as:

```bash
python3 <skill-dir>/scripts/hwpx.py <subcommand> [args]
```

For example (assuming system-wide install):

```bash
python3 ~/.codex/skills/hwpx-edit/scripts/hwpx.py extract input.hwpx --paragraphs
python3 ~/.codex/skills/hwpx-edit/scripts/hwpx.py memo clear input.hwpx -o output.hwpx
```

See `skills/hwpx-edit/SKILL.md` for the full subcommand reference and safety rules.
