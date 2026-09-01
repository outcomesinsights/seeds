---
id: seeds-3dkj
title: The guard helper now prints 'seeds update --content' advice to users of 'seeds answer', which has no such flag — the same defect class we just fixed
status: resolved
type: concern
created_at: 2026-08-26T19:28:41.888291+00:00
updated_at: 2026-08-26T19:38:40.264769+00:00
resolved_at: 2026-08-26T19:38:40.264762+00:00
resolution: "Fixed in 7b1fddd (bead seeds-ijk): guard prose parameterized via a GuardCopy NamedTuple whose fields are all required with no defaults — a default would let the next caller inherit the wrong prose and ship the bug a third time. Tests pin that each command's remediation names that command, including a negative assertion that answer never prints --content. Efficacy: none, green first run."
tags:
  - bug
  - guard
  - remediation
  - answer
  - dx
  - regression
  - shipped-2026-08-26
relationships:
  - target_id: seeds-faxd
    rel_type: relates-to
    created_at: 2026-08-26T19:28:50.593286+00:00
  - target_id: seeds-cb6r
    rel_type: relates-to
    created_at: 2026-08-26T19:28:50.726074+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

Discovered by the implementing agent while shipping seeds-cb6r, 2026-08-26, and reported on both of its receipts as a related defect it deliberately did not fix. Verified afterwards. Recorded because it was INTRODUCED by that fix and would otherwise be lost.

WHAT HAPPENS. `seeds answer` now correctly refuses a re-answer by calling `_guard_content_replacement` (src/seeds/cli.py:121-161) — the existing, tested helper, exactly as the bead specified. But that helper hardcodes its message and its remediation for the `update` command:

    Error: <id> has been edited since it was created -- --content would discard N characters...
      Add to it instead:      seeds update <id> --append "..."
      Discard it on purpose:  seeds update <id> --content "..." --replace

So a user who trips the guard by running `seeds answer` is told about a `--content` flag that `answer` does not have, and is pointed at `seeds update` rather than at `seeds answer <id> "..." --append` / `--replace`, which is what they actually want and what now exists.

THE PART WORTH NOTICING. This is the SAME defect class as the one just fixed in seeds-faxd: guidance that does not match the command it is advising about. There it was a prefix guard described as containment with advice that could never satisfy it; here it is a shared guard describing itself in terms of one caller while a second caller uses it. Shipping the first fix created a fresh instance of its own category — which is worth sitting with, because it suggests the underlying pattern is "remediation text written next to one call site and then shared" rather than two unlucky coincidences.

NOT THE AGENT'S MISS. The bead said, in as many words, to reuse the helper and not invent a second guard, and it was right to — inventing a parallel guard is how the two would drift. The agent flagged this rather than silently widening its scope, which is the correct behaviour. The bead simply did not anticipate that a shared helper carries caller-specific prose.

THE DESIGN CHOICE, and it is genuinely open:
  a) Parameterise the helper — pass the calling command's name and its flag spellings, so one guard renders correct advice for each caller. Most direct, and it scales if a third caller ever appears.
  b) Keep the helper generic — strip the command-specific lines down to what is true for every caller ("this would discard N characters; use the append or replace form of the command you just ran") and lose the copy-pasteable one-liners. Simpler, weaker guidance.
  c) Have the helper return a decision and let each caller print its own remediation. Most flexible, most duplication, and the duplication is precisely the drift risk (a) avoids.

Leaning (a). Whichever wins, the test from seeds-faxd is the model: assert that the remediation a command prints is a command that actually works for THAT command. That property is what neither of these two bugs had, and it is cheap to assert once the shape exists.


--- SHIPPED (2026-08-26, commit 7b1fddd, bead seeds-ijk) ---

Option (a) chosen and built: the guard is parameterized. The caller-specific half now arrives as a `GuardCopy` NamedTuple with four fields -- `reason` ("has already been answered"), `subject` ("answering again"), and the two ready-to-paste `append_cmd` / `replace_cmd` strings. The shared decision logic is untouched. Suite 579 -> 582.

ONE CONSTRAINT ADDED that was not in this seed's three options, and it is the load-bearing part: **every field is required and none has a default.** The defect being fixed was a second caller silently inheriting the first caller's prose, so a default set to either caller's wording would have reintroduced exactly the bug -- and the next caller would have shipped it a third time. Adding a caller now has to mean stating that caller's own remediation. The type's docstring records why, so the reasoning survives the next person who finds the required arguments tedious.

The tests pin the property both bugs lacked: `update`'s refusal must name `seeds update` and its own flags, `answer`'s must name `seeds answer` -- and must NOT contain the string `--content`. That negative assertion is the regression pin, and it is the shape worth copying for any future shared user-facing text.

EFFICACY. Tweaking needed: none. Ruled, built, and green on the first run, with all acceptance criteria met.

Worth noting how cheap this was BECAUSE of how it was found: the implementing agent reported it as a related defect rather than either silently fixing it (scope creep, unreviewed) or silently leaving it (lost). The receipt's `related-defects` line is what turned an incidental observation into a same-day fix, and this is the clearest case so far of that field earning its place.
