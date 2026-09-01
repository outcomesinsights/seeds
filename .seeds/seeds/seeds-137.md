---
id: seeds-137
title: Investigate how 'bd show' renders to terminal in Claude Code; revisit our temp-file workaround
status: resolved
type: exploration
created_at: 2026-05-01T16:37:54.126910+00:00
updated_at: 2026-05-01T16:53:03.145142+00:00
resolved_at: 2026-05-01T16:53:03.145134+00:00
resolution: bd has no special technique; bd show in Claude Code emits plain text the same way seeds show does. Difference is content length, not rendering. Current prime.py protocol (Claude pastes seed content in response) remains the recommended path. Open follow-ups (remove --output-file? add --short mode?) captured in notes for separate decision.
tags:
  - claude-code
  - output
  - beads-inspired
  - ux
  - workaround-revisit
relationships:
  - target_id: seeds-31
    rel_type: relates-to
    created_at: 2026-05-01T16:45:39.841143+00:00
  - target_id: seeds-31.1
    rel_type: relates-to
    created_at: 2026-05-01T16:45:39.931448+00:00
  - target_id: seeds-92
    rel_type: relates-to
    created_at: 2026-05-01T16:45:40.021802+00:00
  - target_id: seeds-138
    rel_type: relates-to
    created_at: 2026-05-01T18:02:15.922050+00:00
  - target_id: seeds-d773
    rel_type: relates-to
    created_at: 2026-08-10T16:11:26.740084+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Context
-------

In seeds-31 we hit a problem where 'seeds show' output was truncated in
the Claude Code CLI terminal — long content required Ctrl+O to expand,
and you couldn't type while expanded. We resolved it in seeds-31.1 by
adding the '--output-file' flag, which writes the rendered seed to a
temp file and prints the path. The agent then reads the temp file. It
works, but it's a workaround, not a clean solution.

Observation
-----------

Beads has a 'bd show' command that appears to render an entire bead's
content to the terminal in a Claude Code session without the same
truncation issue, and from outside inspection it doesn't look like it's
using weird hackery. Worth investigating before we keep building on top
of our temp-file approach.

Goals
-----

1. Read the beads codebase and understand exactly how 'bd show'
   produces its output. Look for: output formatting choices, CLI
   library used, any environment detection (TTY/Claude Code specific
   handling), pagination behavior, anything that distinguishes it from
   a naive print.

2. Compare to the failure mode we hit in seeds-31. Did beads avoid the
   problem by accident (different output shape) or deliberately
   (specific technique)?

3. Decide whether/how to adopt the bd approach in seeds. If feasible,
   the goal is to retire '--output-file' as the default-recommended
   path and have plain 'seeds show' work cleanly in Claude Code.

Open questions
--------------

- What mechanism does bd use? (Stdio handling? Specific renderer? No
  pagination at all?)
- Is the difference about beads vs seeds, or about Go vs Python/Click?
- Does our use of Click force any specific output behavior we'd need
  to override?
- Are there bd edge cases where the same problem still surfaces, or is
  it actually robust?
- Would adopting the bd pattern change the agent's experience in any
  measurable way (token counts, latency, context window)?

Related
-------

- seeds-31: original bug
- seeds-31.1: temp-file workaround decision
- seeds-92: Claude Code output folding workarounds for mani (similar
  domain, may share lessons)

## Investigation findings (2026-04-30)

### How bd produces its output

bd show (cmd/bd/show.go) writes plain text via fmt.Print directly to
stdout. Notes:

- No pager. There is a ui.ToPager helper (internal/ui/pager.go) that
  pipes through less when stdout is a TTY and content exceeds terminal
  height, but show.go does not call it.
- Markdown rendering goes through ui.RenderMarkdown
  (internal/ui/markdown.go). That function consults ShouldUseColor()
  and returns the raw markdown string when color is disabled. Color is
  auto-disabled when stdout is not a TTY (Claude Code captures stdout
  to a buffer, so this is true inside a Bash tool call).
- All ui.Render* styling helpers wrap text with lipgloss. With color
  disabled, they return the input unchanged. So no ANSI escape codes
  are emitted in Claude Code.
- There is an IsAgentMode() check in internal/ui/styles.go that
  triggers on BD_AGENT_MODE=1 or the env var CLAUDE_CODE. Claude Code
  actually sets CLAUDECODE=1 (no underscore), so this branch is
  dormant — but it does not matter, the no-TTY branch already produces
  plain text.

Verified by piping bd show through od -c: only Unicode glyphs, no
ANSI escapes.

### Comparison to seeds show

seeds show already does the same thing structurally: writes plain text
via click.echo, no ANSI styling, no markdown rendering, no pager.
Output is straight ASCII. There is no clean Markdown-renderer /
TTY-detection / pager trick that bd is using and seeds is not.

### Why bd "appears" not to truncate

The most plausible explanation is output length, not output technique:

- A typical bd issue header + description renders in ~7-15 lines.
- A typical seeds show with content + children + relationships easily
  hits 40-70 lines (seeds-137 itself is 63 lines).

Claude Code folds Bash tool output above some line/byte threshold. bd
output usually stays under it; seeds output usually exceeds it.

This is consistent with what we already concluded in seeds-31 final
solution and seeds-92: ALL tool output (Bash and Read) is folded once
it exceeds the threshold. The only path that lets the user see content
reliably is the prime.py protocol — Claude pastes seed content into
its response text.

### Decision

Nothing to implement. There is no bd technique to copy. The current
prime.py guidance ("paste seed content in your response when
discussing with the user") remains the recommended path. The
--output-file flag continues to exist but is not the recommended path
for end-user display (it never was, after the seeds-31 reframe).

Open follow-ups for future consideration:

- Decide whether to remove --output-file entirely (it helps agent-only
  reads when output is huge, but seeds-92 shows Read output is also
  folded for the user, so its UX value is narrow).
- Consider adding a --short / compact mode similar to bd, which would
  shrink the typical seeds show output and reduce how often the fold
  kicks in for casual reads.

Tests: 216 passing, no source changes made.
