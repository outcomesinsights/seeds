---
id: seeds-gnl4
title: How much context should seeds spend teaching an agent to use it, and where should the rest live?
status: captured
type: question
created_at: 2026-09-13T20:28:39.393951+00:00
updated_at: 2026-09-13T20:31:09.304950+00:00
tags:
  - prime
  - context-budget
  - agent-onboarding
  - cli-ux
  - 2026-09-13
relationships:
  - target_id: seeds-gi9k
    rel_type: relates-to
    created_at: 2026-09-13T20:31:09.304333+00:00
---

Raised by @aguynamedryan 2026-09-13, immediately after trellising "guidance must
ship in the package" (seeds-gi9k) — and it is the direct tension with it. If the
package is the only carrier that reaches every machine, everything wants to go
into `seeds prime`; but prime is paid for on every session of every agent.

Explicitly filed as thinking, not as work: *"this is just some thinking that
doesn't necessarily need to be pursued at this time."*

## Measured today, so the question is not hypothetical

```
seeds prime output      257 lines   20,796 chars   ~5,200 tokens
  static guidance       185 lines
  live digest            72 lines
literal text in prime.py            13,668 chars
```

~5,200 tokens injected into every session, before the agent has done anything.
And the static half grew three times in two days — the fencing rule, the
long-body routes, the `-F` warning, the shell-word rule. Each addition was
individually justified; none was weighed against the total.

## The options he named

1. **Lean prime + detailed `--help`.** Help is read on demand and costs nothing
   standing. It is also already shipped and already versioned with the code.
2. **Lean prime + shipped documents** an agent can read when it needs them —
   requires prime to name them, and requires the agent to choose to read.
3. **Do nothing yet.** 5K tokens may simply be affordable.

## The discriminator worth trying before picking an option

Not "is this important" — everything in prime is important, which is how it got
there. The question that actually sorts:

**Does the agent need this BEFORE it acts, and is the failure silent?**

- YES, both -> prime. The shell-word rule is the type case: violate it and the
  seed is corrupted with no error, so an agent that learns it afterwards learns
  it too late. Same for "fence anything that must stay verbatim".
- NO -> `--help` or an error message. Tag-edit syntax, the status vocabulary,
  the difference between `--append` and `--content`: get these wrong and the
  CLI tells you immediately. Standing context buys nothing that the error
  message does not.

By that test, a good deal of the current 185 lines is command reference that
would be better as help text, and the load-bearing rules are a much smaller set.

## What makes this hard to settle

- **prime is not guaranteed either.** It is injected by a Claude Code hook; a
  different harness may never call it. That argues for the load-bearing rules
  living in `--help` and error text REGARDLESS, with prime as the fast path
  rather than the only path — which weakens option 1's premise that they are
  alternatives.
- **A fresh agent does not know what it does not know.** Option 2 depends on an
  agent choosing to read a document about a hazard it has not met. The shell-word
  class is evidence against that: `--content-file` existed and was documented in
  help for two weeks while the corruption kept happening.
- **No way to test the fresh-agent path today** (seeds-gi9k's open question).
  Without it, any trim is a guess about what a naive agent still gets right.

## The cheap first move, if this is ever picked up

Measure, do not redesign. Take the current prime, sort every block by the
discriminator above, and see what the load-bearing subset actually weighs. If it
is 60 lines, the answer is obvious. If it is 150, there is nothing to trim and
option 3 is correct.
