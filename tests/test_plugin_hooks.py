"""Pin the plugin's session hooks (bead seeds-oiy, ruled on seed seeds-i9y6.1).

``bd prime`` reaches every session because the beads plugin declares
SessionStart and PreCompact hooks in its OWN manifest. ``seeds prime`` once
reached sessions through a hand edit to the user's settings file, which a
settings regeneration wiped without a word. A hook in the package survives that
and reaches every machine that ran ``seeds skills install`` (seeds-gi9k), so the
manifest is the one place these may live, and this test is what keeps them
there.

The check reads the repo source tree, so it validates exactly what gets
committed.
"""

import json
from pathlib import Path

import pytest

PLUGIN_JSON = (
    Path(__file__).resolve().parent.parent
    / "src/seeds/plugin/claude-plugin/.claude-plugin/plugin.json"
)


@pytest.mark.parametrize("event", ["SessionStart", "PreCompact"])
def test_plugin_injects_seeds_prime(event):
    hooks = json.loads(PLUGIN_JSON.read_text())["hooks"]

    assert hooks[event] == [
        {"matcher": "", "hooks": [{"type": "command", "command": "seeds prime"}]}
    ]


def test_the_hooks_run_the_short_form_not_the_full_reference():
    """``--full`` is ~25,000 characters; injecting it at every start and every
    compaction is the context cost the short form exists to avoid."""
    text = PLUGIN_JSON.read_text()

    assert "--full" not in text
