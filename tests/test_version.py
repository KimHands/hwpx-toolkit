import json
from pathlib import Path

import _hwpxlib as lib

PLUGIN_JSON = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"


def test_library_version_matches_plugin_manifest():
    manifest = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    assert lib.__version__ == manifest["version"]
