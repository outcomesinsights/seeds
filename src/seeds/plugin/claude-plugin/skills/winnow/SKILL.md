---
name: winnow
description: Use when the user wants a health check on the *thinking* in the seed corpus rather than on its files — resolved seeds that contradict each other, resolutions resting on a premise that has since moved, deferrals nobody came back to, seeds nothing is blocking any more (e.g. "winnow the seeds", "audit the corpus", "is our deliberation still sound?"). Runs `seeds winnow`, judges the candidates it scopes, and presents findings for the user to rule on.
---

# Winnow the corpus

`seeds winnow` asks the third health question: `seeds check` asks whether the FILES are valid, `seeds doctor` whether the STORE is healthy, `winnow` whether the THINKING is. The verb is deterministic, tested, and read-only — it narrows and then stops. **This skill is the judgment half**, and only that half: it reads what the verb scoped, decides which candidates survive, and presents findings for the user to rule on.

The failure this design exists to prevent is an auditor that cries wolf. One bad soft finding trains the reader to skip the whole report, and then the factual half stops being read too. Every rule below is that guard.

Do this once when invoked. Do not adopt it as default behavior for later turns.

## 1. Run the verb — never scan the corpus yourself

    seeds winnow --json

`--flavor` (repeatable: `neglect`, `unblocked`, `unresolved`, `contradiction`, `staleness`, `outcome`) narrows the run; `--since` replaces every age cutoff with one point (`3m`, `2026-05-08`). The JSON is `{corpus: {seeds, edges}, flavors, facts, candidates}`, and each finding is `{tier, flavor, code, seed_ids, message, action, evidence}`. `tier` is `fact` or `candidate` and it decides everything that follows.

**Report only what the verb surfaced.** Do not go hunting the corpus for what it missed. Its contradiction rule is negation-scoped by construction, so a disagreement phrased as a *quantifier* change is out of its reach — `seeds-138` ("Claude Code folds **long** tool output") and `seeds-92` ("folds **ALL** tool output") are linked, do genuinely conflict, and are not reported. That miss is deliberate: the looser rule that caught the pair produced 5 false positives out of 7, including seeds that plainly agreed. If you think the rule has a systematic gap, file a seed about the rule. Do not widen it by hand inside a report.

## 2. Pass the FACTS through unedited

`tier: "fact"` — `neglected-deferral`, `unblocked-and-open`, `long-unresolved`. These are graph-and-date facts. A deferral untouched for eight months either is or is not; there is nothing here to judge and adding judgment only makes them less trustworthy. Reproduce each finding's `message`, `evidence` and `action` as the verb wrote them.

Permitted: grouping by flavor, and putting the flavor most likely to be actionable first (`unblocked-and-open` usually is — every blocker closed and the seed still open). Not permitted: dropping one, ranking them by your sense of importance, softening one with a hedge, or promoting your own reading of a seed into this section.

## 3. Judge the CANDIDATES — expect to discard most

`tier: "candidate"` — `contradiction-candidate`, `staleness-candidate`, `outcome-candidate`. The verb is explicit that these are leads, not verdicts, and each carries in `action` the judgment still to be made. `seeds show` both endpoints and actually read them before you decide anything.

- **Contradiction** — the two seeds are linked and their quoted lines have opposite polarity about a shared subject. Do they genuinely conflict? Two related seeds usually *agree*, or talk past each other, or one already says it supersedes the other. Any of those, drop it.
- **Staleness** — a resolved seed citing a checkable premise: a version, a count, a dated measurement. Go and check it. Read the file, the release notes, the current number. If you cannot say **what changed**, drop it — age is not evidence, and "this feels stale" is exactly the finding this skill refuses to emit.
- **Outcome** — a resolved seed naming downstream beads. Whether the shipped thing did what the seed hoped is not in the corpus at all; it is in the code, the tests, and whoever used it. Check, then report only where you can say something. This flavor arrives in bulk — a healthy corpus can raise two dozen — so triage it: surface the few worth the user's time and state how many you set aside, rather than relaying the list.

**Cite or drop.** A reported finding names the specific seed IDs and quotes the specific conflicting or moved text. A finding you cannot cite is not reported, silently.

Discarding is the normal outcome, not a failed pass.

## 4. Report — two sections, never one

    314 seeds, 427 edges. Flavors: all.

    FACTS (62) — no judgment needed
      … the verb's lines, unedited …

    CANDIDATES — 3 reported, 25 read and set aside
      … each one judged, each one citing IDs and text …

Keep the two apart even when a candidate looks certain. Confidence goes in your words ("both seeds are unambiguous; seeds-138 is the later and the narrower claim"), never in a promotion up into the FACTS list — a judged candidate is still a candidate, and one wrong entry in the factual section costs the whole report its credibility. Say how many candidates you read and set aside, so the ones you kept are visibly a selection rather than everything the verb emitted.

## 5. "Nothing to report" is a good outcome

If no fact fired and no candidate survived judgment, say exactly that — "314 seeds, 427 edges, nothing to report" — and frame it as the corpus being healthy, not as the pass coming up empty. Never pad a short report with marginal findings to look productive. Most passes over a well-tended corpus should be short.

## 6. Apply the rulings

Present first; the verb writes nothing and neither does this skill until the user rules. Then apply, in a batch, echoing what you ran:

- **Contradiction upheld** — the user says which one stands. Append the correction to the superseded seed with `seeds update <id> --append` (never `-c/--content`, which *replaces* and would destroy the deliberation), naming the seed that supersedes it, and `seeds link <id> --relates-to <winner>` if no edge records the relationship yet.
- **Premise confirmed moved** — `seeds update <id> --append` with what changed and what it means for the conclusion. Reopen with `seeds explore <id>` only if the user wants the decision reconsidered.
- **Unblocked-and-open** — `seeds resolve <id> -r "<outcome>"`, or record what the user says is still open.
- **Neglected deferral** — `seeds explore <id>` to pick it back up, or `seeds abandon <id> -r "<reason>"` to let it go.
- **Long-unresolved** — resolve it, abandon it, or park it with `seeds defer <id>`; `defer` takes no reason flag, so write the reason first with `seeds update <id> --append`.

Leave anything the user did not rule on untouched. An unresolved finding is a fine place to stop; a finding closed on your own judgment is not.
