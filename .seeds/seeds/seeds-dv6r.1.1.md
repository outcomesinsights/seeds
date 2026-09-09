---
id: seeds-dv6r.1.1
title: Fence anything in a seed body that must stay verbatim
status: resolved
type: decision
parent: seeds-dv6r.1
created_at: 2026-09-08T22:06:56.132333+00:00
updated_at: 2026-09-09T21:31:15.030101+00:00
resolved_at: 2026-09-09T21:31:15.030094+00:00
resolution: "Shipped, with its owner changed: the WRITER fences literal text, not the author. Three tiers — fence the literal run inside a paragraph, format anyway where only spacing moves, store verbatim where meaning would change. 64 of 1,293 bodies gained a fence, 2 kept verbatim. The rule still holds for agents and is in seeds prime. Efficacy: MINOR, and the tweak was a ruling rather than a defect — the lesson is to name WHO obeys a rule, because 'the author fences it' and 'the writer fences it' are different features and only one works when the author is an agent nobody is watching."
tags:
  - storage
  - format
  - authoring
  - formatter
  - 2026-09-08
---

Ruled by @aguynamedryan, 2026-09-08, while settling the write-time formatter in
seeds-dv6r.1.

**Anything in a seed body that must survive as literal text gets a fence.** Logs,
command output, tracebacks, SQL, file listings, hand-aligned columns, YAML
samples — if the characters matter, they go in a fenced block.

This stops being style advice the moment the writer formats bodies. Measured
against mdformat, a fenced block is preserved byte for byte; an unfenced one is
not, and the damage is silent:

- a pasted traceback loses its indentation and gains escapes (`*args` -> `\*args`)
- a 2-space-indented SQL block is flattened to column 0, and under prettier its
  literal `count(*)` became `count(_)` (seeds-183, corpus-wide measurement)
- an unfenced YAML sample whose `---` lines CommonMark reads as setext headings
  collapses into a heading (an oimnibus seed)
- hand-aligned two-column blocks collapse to single spaces — 84 files corpus-wide

Every one of those is the author's choice of layout markdown does not have. A
fence is the construct that does have it, and it survives *any* formatter, which
is why this is the rule rather than "exclude the store from formatters".

The audience is agents, since agents write nearly every seed body. So the delivery
mechanism matters more than the rule: `seeds prime` is what actually reaches an
agent in any repo, which makes it the place this belongs — not one repo's
CLAUDE.md.

## AS BUILT (2026-09-09) — the rule became the writer's job, not the author's

Captured above as an authoring rule. Ruled otherwise the same day
(@aguynamedryan): *"agents are the only ones ever using the seeds CLI, so no one
is 'pasting an unfenced traceback' unless that is an agent. I want these things
handled rather than bothering the user."* So the writer fences its own literal
text, in three tiers, silently:

1. fence the literal RUN inside a paragraph — the aligned or over-indented
   lines, not the paragraph, which would set a prose lead-in in monospace.
   Purely additive: two fence lines, indentation kept, not one character
   removed, which is what lets `seeds convert` keep verifying a body landed
   verbatim.
2. where what remains differs only in spacing, format anyway — those are
   hand-indented quotations, where every word survives and a fence would be
   wrong because they are prose.
3. where formatting would still change what the body MEANS, store it exactly
   as it came, and report it as `body-kept-verbatim`.

Measured over 1,293 non-empty bodies: 64 gained a fence, 2 were stored verbatim.

**The rule as written still holds for agents**, and is in `seeds prime` — a
fence is still the right thing to type, and the three files that ended up in
tier 3 are exactly the bodies where nobody typed one. What changed is that
failing to type it is now recoverable rather than lossy.

**A relaxation of tier 3 was tried and reverted, and the reason is worth
keeping.** Those three bodies each contain a line of `====` or `----`, which
CommonMark reads as a setext heading underline; the rendered difference is only
newlines inside a heading, which HTML collapses. Relaxing the comparison to
ignore that made all three formattable — and let the formatter rewrite a fork
conflict file, because git's `=======` separator is *also* a valid setext
underline: `<<<<<<< database` became `# \<<\<<\<<< database`. The strictness
is protecting merge tooling, not being fussy.

## EFFICACY

**Minor tweaking, and the tweak was a ruling rather than a defect.** The rule
was right; its owner changed. The one thing a better seed would have said: name
who is expected to obey a rule, because "the author must fence it" and "the
writer fences it" are different features and only one of them works when the
author is an agent nobody is watching.
