---
id: seeds-i9y6.1
title: Why is seeds prime not injected at session start the way bd prime is, and should the seeds plugin add the hook?
status: exploring
type: question
parent: seeds-i9y6
created_at: 2026-09-30T19:56:30.176056+00:00
updated_at: 2026-09-30T20:05:47.017585+00:00
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

## Exploration 2026-09-30: mimic bd prime's size (Ryan: "let's mimic bd prime's output so we're not context hogs")

**Measured:** bd prime is 3,326 characters (~830 tokens): a title, a recovery note, command bullets grouped by task, and a few workflow blocks. seeds prime is 24,759 characters: about 14,200 of workflow reference (largest parts: Creating 2,400, What to Capture 1,550, Recovering 1,250, Finding Work 1,230) and about 10,300 of digest (20 recently updated, 10 in exploration, 35 open questions). `seeds prime --help` already says it is "for Claude Code hooks", so it was built for startup and never wired.

**Proposed shape (not ruled):**

1. The plugin manifest gains SessionStart and PreCompact hooks running `seeds prime`, exactly as beads does. PreCompact matters most: compaction is when guidance is lost. No guard is needed outside a store, since seeds prime exits 0 silently there.
2. `seeds prime` itself becomes the SHORT form, mirroring bd prime (one command, hook-sized). Today's full text moves to `seeds prime --full`. The short form's recovery line points there. (The alternative, keeping prime full and adding `--brief` for the hook, leaves the default as the context hog anything else would call.)
3. The digest shrinks to one computed count line plus a pointer to `seeds ready`; the lists live in `--full`.
4. The first section is the seed-vs-bead boundary, the fix seeds-i9y6 is about: unruled goes in a seed, ruled work in a bead, and a bead's --design holds only decisions already made.
5. The correction rule follows seeds-zxq8's option C. It references `seeds update --edit`, which bead seeds-5i1 adds, so this ships after 5i1, or the line waits for it.

**Draft short form (2,487 characters, ~620 tokens):**

```markdown
# seeds Workflow Context

> **Context Recovery**: this is the short form, injected at session start and after compaction.
> Run `seeds prime --full` for the full reference: capture examples, every command, current seeds.

## Seed or bead? (decide BEFORE you file anything)
- **Unruled → seed.** A question, an option list, a "Not ruled. Directions: (a)… (b)…", a design fork inside a bug report. The person rules; the seed holds the argument.
- **Ruled → bead.** Work with a decision behind it. A bead's `--design` field holds only decisions already made.
- A report that is part defect, part design question is BOTH: a bead for the defect, a seed (or `seeds ask` on an existing seed) for the fork.
- Confirming a decision records it in the seed; it does not authorize building it.

## Capture the journey, not just the conclusion
- Capture DURING the work: what you checked and why, what you found (with counts), what the user said (verbatim).
- Eliminated options and invalidated assumptions are worth a line each.
- **Fence** anything that must stay verbatim (logs, output, SQL, tracebacks). Bodies are formatted on write; unfenced literals get mangled.

## Essential Commands
- `seeds jot "thought"`: capture in one line, title only
- `seeds create -t "Title" --type idea|question|decision|exploration --content-file F`: a seed with a body; keep multi-paragraph bodies out of argv
- `seeds ask "question?" --seed <id>` / `seeds answer <id> "answer"`: questions attached to a seed
- `seeds ready` · `seeds list` · `seeds show <id>` · `seeds search "<regex>"`: find and read
- `seeds update <id> --append -` (body on stdin): add to a seed's deliberation, the normal way to write to an existing seed
- `seeds explore` / `defer` / `resolve -r "outcome"` / `abandon -r "why"` `<id>`: lifecycle
- **WARNING**: `-c/--content` REPLACES a body and is refused on any non-empty one. Never use it to add.

## Correcting what a seed says
- A fact that turned out **false**: fix it in place with `seeds update <id> --edit OLD NEW`.
- A position we **moved past**: append a dated note (`RULED 2026-09-30: …`, `UPDATE …`). Do not delete the old position.

## Session end
- `seeds check`, then commit `.seeds/seeds/*.md` like any source file. There is no export step.
- Commit new seed files BEFORE starting implementation, so they don't get swept into the implementation's commits.

**Store:** <N> seeds · <Q> open questions · <E> exploring (computed). `seeds ready` shows what needs attention.
```

## RULED 2026-09-30 (Ryan), on the five points above

1. Yes: SessionStart and PreCompact hooks in the seeds plugin manifest, running `seeds prime`, as beads does.
2. `seeds prime` IS the short form. The full reference is `seeds prime --full`.
3. The digest is one computed count line in the short form; the lists live in `--full`.
4. The seed-vs-bead section leads, worded as in the draft.
5. This lands after bead seeds-5i1 (`seeds update --edit`), because the short form names `--edit`.
   Implementation: see the bead sourced from this seed.

## History, found 2026-09-30: seeds prime WAS injected at startup, until March

- 2026-03-12: a bead (recorded in commit f1391a0's beads export) closed with "Implemented seeds hooks integration": seeds prime made silent outside a seeds project, `find_seeds_dir()` added, seeds installed globally via uv tool, and "seeds prime hooks [added] to SessionStart and PreCompact in ~/.claude/settings.json". The hooks were HAND-EDITED into the user's settings file.
- 2026-03-21, nine days later: home-manager commit e5d7772 ("manage settings.json via nix with writable symlink") made ~/.claude/settings.json nix output, regenerated on every switch from modules/claude-code.nix. Neither `seeds prime` nor `bd prime` was carried into the nix config (0 matches in e5d7772), and `seeds prime` has never appeared in home-manager's history since. The seeds hook was silently wiped then.
- bd prime survived because the beads plugin declares SessionStart and PreCompact hooks in ITS OWN plugin.json, which home-manager does not rewrite. seeds had only the hand-edited copy.
- So for about six months, seeds guidance has reached agents only when something told them to run `seeds prime`: this repo's CLAUDE.md, a skill, or the user. That is a long-standing baseline, not last week's change, so it does not by itself explain the recent drift seeds-i9y6 describes.
- Lesson, and why bead seeds-oiy puts the hooks in the plugin manifest: a hook in the PACKAGE survives settings regeneration and reaches every machine; a hand edit to user settings does neither (seeds-gi9k). The seeds plugin is already installed on every host through home-manager (modules/claude-code/plugins.nix: `seeds@seeds-marketplace`, pointing at the nix store copy of the seeds source), so a manifest hook goes live on the next seeds flake bump and switch.
