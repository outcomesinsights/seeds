"""Guards that the version stays single-sourced (bead seeds-5uw).

The canonical version is ``src/seeds/__init__.py`` (``__version__``).
``pyproject.toml`` derives it dynamically (hatchling), so it cannot drift. The
two Claude Code plugin manifests must hold a matching literal version; these
tests fail loudly the moment one falls behind, pointing at ``just bump-version``.

The checks read the repo source tree directly (not the installed package) so
they validate exactly what gets committed, regardless of install mode.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_PY = REPO_ROOT / "src" / "seeds" / "__init__.py"
PLUGIN_JSON = REPO_ROOT / "src/seeds/plugin/claude-plugin/.claude-plugin/plugin.json"
MARKETPLACE_JSON = REPO_ROOT / "src/seeds/plugin/.claude-plugin/marketplace.json"


def _canonical_version() -> str:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', INIT_PY.read_text())
    assert match, "could not find __version__ in src/seeds/__init__.py"
    return match.group(1)


def test_plugin_json_version_matches_canonical():
    version = _canonical_version()
    data = json.loads(PLUGIN_JSON.read_text())
    assert data["version"] == version, (
        f"plugin.json version {data['version']!r} != __version__ {version!r}; "
        f"run `just bump-version {version}`"
    )


def test_marketplace_json_versions_match_canonical():
    version = _canonical_version()
    data = json.loads(MARKETPLACE_JSON.read_text())
    versions = [plugin["version"] for plugin in data["plugins"]]
    assert versions and all(v == version for v in versions), (
        f"marketplace.json plugin versions {versions} != __version__ {version!r}; "
        f"run `just bump-version {version}`"
    )
