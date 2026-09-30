---
id: seeds-i9y6.1
title: Why is seeds prime not injected at session start the way bd prime is, and should the seeds plugin add the hook?
status: captured
type: question
parent: seeds-i9y6
created_at: 2026-09-30T19:56:30.176056+00:00
updated_at: 2026-09-30T19:56:30.176056+00:00
tags:
  - cutting
---

**What we were discussing:** Ryan asked (2026-09-30): "why isn't seeds prime part of claude's startup thingy like beads prime is?" Every Claude Code session gets `bd prime` injected at startup. None gets `seeds prime`. So agents start each session knowing beads' workflow and not seeds'.

**Why it came up:** Right after Ryan ruled option C on seed seeds-zxq8 (how corrections to seed bodies are written). That ruling, like most seeds guidance, reaches agents through `seeds prime`. The parent seed seeds-i9y6 (agents drift to capturing deliberation in beads) had already named this priming gap as its first suspected cause. This cutting is that one question on its own.

**Established (verified on titan, 2026-09-30):**

- The mechanism is the plugin manifest. The beads plugin's `.claude-plugin/plugin.json` (beads 0.60.0, in ~/.claude/plugins/cache/beads-marketplace/) declares `"hooks": {"SessionStart": [... "command": "bd prime"], "PreCompact": [... "command": "bd prime"]}`, so bd prime is injected at session start AND again before every compaction. The seeds plugin's manifest (src/seeds/plugin/claude-plugin/.claude-plugin/plugin.json) has no `hooks` key, and the plugin ships no hooks directory. Neither ~/.claude/settings.json nor the repo's .claude/settings\*.json runs seeds prime. Nobody chose to leave it out; it was never wired.
- Both are silent outside their store: in a directory with no .seeds, `seeds prime` prints nothing and exits 0, and `bd prime` does the same without .beads. So a SessionStart hook would cost nothing in repos without a seed store.
- The real cost is SIZE. `seeds prime` is about 24,700 characters (roughly 6,000 tokens). `bd prime` is about 3,300 characters (roughly 830). As a SessionStart plus PreCompact hook, seeds prime would add about 6,000 tokens at every start and after every compaction, in every repo with a seed store (25 non-archived repos).
- The seeds repo's own principle (seeds-gi9k): guidance an agent needs must ship IN the package, because a CLAUDE.md reaches one machine. A plugin hook is in the package; the current state (guidance reaches an agent only if something tells it to run seeds prime) is the gap that principle names.

**Open, the question this is parked on:**

1. Add SessionStart and/or PreCompact hooks to the seeds plugin manifest running `seeds prime`, the way beads does? PreCompact matters because compaction is exactly when guidance is lost.
2. The size: inject the full ~6k-token prime, or a short startup form (a `seeds prime --brief` or `--hook` mode: the seed-vs-bead boundary, the few commands, the correction rule, and a pointer to full `seeds prime`) with the full text on demand? bd prime's ~830 tokens is the working comparison.
3. What the injected text must contain to fix the parent seed's drift: at minimum the boundary between a seed (anything unruled) and a bead (ruled work), stated where bd prime's "`--design` Record design decisions" line otherwise wins by default.
4. Does the hook need a guard for machines where `seeds` isn't installed, as the commit recipe has (`command -v seeds || exit 0`)? The plugin is installed from the seeds package, so seeds is probably always present, but that needs checking.
