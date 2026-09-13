---
id: seeds-gi9k
title: Guidance that does not ship with the package reaches exactly one machine
status: resolved
type: concern
created_at: 2026-09-13T20:24:51.177643+00:00
updated_at: 2026-09-13T20:31:09.394277+00:00
resolved_at: 2026-09-13T20:25:38.511364+00:00
resolution: 'Recorded as a trellis in `CLAUDE.md` on 2026-09-13: Guidance an agent needs in order to use seeds correctly must ship IN the package — prime, --help, and error text — because a CLAUDE.md or memory file reaches exactly one machine and seeds runs on many.'
tags:
  - distribution
  - agent-onboarding
  - prime
  - cli-ux
  - 2026-09-13
  - trellis
relationships:
  - target_id: seeds-gnl4
    rel_type: relates-to
    created_at: 2026-09-13T20:31:09.304333+00:00
---

Raised by @aguynamedryan 2026-09-13, while fixing the shell-substitution class:

> "Seeds is going to be used across multiple hosts by different users with
> different setups for Claude Code. Whatever guidance we provide really needs
> to be built into seeds to teach any agent that might interact with it on any
> machine. I've been using seeds extensively on my computers with my Claude and
> I'm sure it has adapted a lot of its behaviors to work with seeds, and I
> don't know how easily that's going to translate to anyone else using seeds
> fresh when their Claude has never seen it before."

## The concern, stated plainly

Every piece of guidance that lives OUTSIDE the seeds package reaches exactly
one machine. `~/.claude/CLAUDE.md` is a nix symlink on this host. Harness
memory under `~/.claude/projects/<slug>/memory/` is per-user and per-project.
A `bd remember` note lives in one repo. None of it ships.

What ships is: the package, `seeds prime`, the CLI's `--help`, and the text of
its error messages. **Those four are the whole surface for teaching an agent
that has never seen seeds before.**

## The proof case that made it concrete

Writing a seed body through a double-quoted shell word silently corrupts it —
every POSIX shell substitutes backticks and `$expansions` before seeds runs, so
a body quoting a command is replaced by that command's output. Six incidents in
three months across four repos, two of them silent content loss found later.
44% of 1,904 seed bodies on this machine contain a backtick.

The mitigations that existed by 2026-09-13 were: `--content-file`/`--content -`
(shipped), a line in `seeds prime` (shipped), and a note in one repo's harness
memory (does not ship). **It kept happening anyway**, because all three
required the agent to already know to choose the safe route, and the punishment
for not choosing it was silent.

What finally changed the shape was a REFUSAL in the tool: `--content` now
rejects a body that spans lines and names the safe routes in the error. That
teaches at the moment of the mistake, to any agent, on any machine, with no
prior exposure to seeds and no configuration.

## The asymmetry worth remembering

An adapted agent and a fresh one are indistinguishable from inside this repo.
Everything works here, so nothing signals the gap. The only reliable test is to
ask: *if this guidance vanished from every CLAUDE.md and memory file on earth,
would a fresh agent still be told?* If the answer is no, the guidance is not
shipped — it is a local habit that happens to be written down.

## Open

- Is there any way to actually TEST the fresh-agent path? A container with no
  memory, no CLAUDE.md, and only the package, given a task that requires seeds.
  Nothing like that exists today, and without it this stays a judgement call.
- `seeds prime` is only read if the host injects it. Claude Code does via a
  hook; another harness may not. So even prime is not guaranteed, which argues
  for the CLI's own help and error text carrying the load-bearing rules.
