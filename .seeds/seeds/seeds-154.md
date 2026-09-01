---
id: seeds-154
title: "Can the seeds CLI programmatically drive a Claude Code plugin install (option 2) end-to-end, matching the ease of a simple file-copy command (option 1)? Sub-questions: (1) Is there a Claude Code CLI command/API for installing a plugin from a local path? (2) Can we keep the plugin local (no remote registry) during early iteration? (3) Does plugin install require user confirmation each time, or can the seeds CLI drive it non-interactively? (4) How does plugin uninstall/update work — can the seeds CLI manage the lifecycle? If yes to all, ship option 2 today; if any are 'no' or 'unclear,' ship option 1 first and migrate later."
status: resolved
type: question
created_at: 2026-05-27T18:30:37.494866+00:00
updated_at: 2026-05-27T18:40:04.969609+00:00
resolved_at: 2026-05-27T18:40:04.969601+00:00
relationships:
  - target_id: seeds-152.3
    rel_type: questions
    created_at: 2026-05-27T18:30:37.499182+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Yes — option 2 (Claude Code plugin) is viable with comparable install ease. Decision in seeds-152.3 resolves to option 2.

## Mechanism

Bundle a marketplace directory inside the seeds Python package. The seeds CLI registers the marketplace and installs the plugin via the existing `claude plugin` subcommands:

```
claude plugin marketplace add <bundled-path>        # idempotent
claude plugin install seeds@seeds-marketplace --scope user
claude plugin update seeds@seeds-marketplace        # after uv tool upgrade seeds
```

All non-interactive. The `seeds:*` skill namespace is automatic via plugin distribution.

## Sub-questions resolved

1. **Local-path install**: yes. `claude plugin install` works against any registered marketplace, including a local directory registered via `claude plugin marketplace add <dir>`.
2. **Local-only plugins**: yes. No remote registry needed. Confirmed by inspecting beads' install — it lives at `~/.claude/plugins/marketplaces/beads-marketplace/` as a local clone.
3. **Non-interactive install**: yes. The `claude plugin install/update/uninstall` commands accept `--scope user` and run without prompts.
4. **Lifecycle**: `claude plugin update <name>@<marketplace>` refreshes from the marketplace source. `claude plugin uninstall` removes. Both can be driven from the seeds CLI.

## Plugin layout (minimum)

Inside the seeds Python package, ship something like `src/seeds/plugin/`:
```
src/seeds/plugin/
├── .claude-plugin/
│   └── marketplace.json          # marketplace manifest, lists plugins
└── claude-plugin/
    ├── .claude-plugin/
    │   └── plugin.json           # plugin manifest (name, version, description)
    └── skills/
        └── feedback/
            └── SKILL.md          # the feedback skill
```

Reference: `~/.claude/plugins/marketplaces/beads-marketplace/.claude-plugin/marketplace.json` uses this exact pattern — marketplace.json with `"plugins": [{ "name": "beads", "source": "./claude-plugin", "version": "0.60.0" }]`.

## Implementation entry point

A `seeds skills install` command in the CLI:
```python
import importlib.resources
import subprocess

with importlib.resources.path('seeds', 'plugin') as plugin_path:
    subprocess.run(['claude', 'plugin', 'marketplace', 'add', str(plugin_path)],
                   capture_output=True, check=False)
    subprocess.run(['claude', 'plugin', 'install',
                    'seeds@seeds-marketplace', '--scope', 'user'],
                   capture_output=True, check=False)
```

After `uv tool upgrade seeds`, the same command (or a sibling `seeds skills update`) runs `claude plugin update seeds@seeds-marketplace` to refresh from the bundled marketplace.

## What this unlocks

- The `seeds:*` skill namespace the user wanted.
- Native Claude Code lifecycle (`claude plugin list`, `claude plugin disable`, etc.).
- A clean reference template (the beads marketplace) to model the layout on.
- No publishing required — the marketplace lives inside the Python package and is registered locally.
