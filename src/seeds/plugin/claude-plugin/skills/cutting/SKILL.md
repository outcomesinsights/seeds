---
name: cutting
description: Use when the user wants a live side-topic set aside without losing it — "take a cutting", "set that aside", "park that for later", "we'll come back to this". Captures the topic *plus* enough of the surrounding deliberation, excerpted into the seed body, that a later session can resume it cold.
---

# Take a cutting

A long session throws off more topics than it can follow. Each one that surfaces mid-thread is real — not rejected, just unheld — and working it would mean abandoning the thread you are on, so it gets parked. In the garden metaphor a **cutting** is a piece taken off the living plant with enough stem to root somewhere else: not the whole conversation, and not merely the topic's name, but the topic together with the tissue it needs to grow on its own.

`seeds jot "…"` is the opposite trade, and deliberately so — title-only, minimum friction, tuned to catch a thought before it escapes. A cutting spends more at capture time so the resume is cheap, because **the cost of restarting cold is why parked topics stay parked.** A one-line jot preserves *that* the topic existed; it does not preserve the argument that made it worth raising. Weeks later someone reads the line, cannot reconstruct why it mattered, and parks it again.

There is no `seeds cutting` verb. A cutting is an ordinary seed created through `seeds create` — the judgment about *what to put in the body* is the whole of this skill.

Do this once, when invoked. Do not adopt this as default behavior for later turns.

## What the body must carry

One seed, whose body answers four questions for a reader who was not in the room:

1. **What was being discussed** — the topic itself, stated so it stands alone. Not "the thing above."
2. **Why it came up** — what in the main thread surfaced it. This is what makes the topic worth reopening rather than re-deriving.
3. **What was already established** — points agreed, options ruled out, constraints discovered. Without this the resume redoes work that was already done.
4. **What remains open** — the specific question the topic is parked *on*. This is what turns the seed back into a next step.

Write it for a different agent, on a different machine, months later. If any of the four would only make sense to someone who read this session, it is not written yet.

## Carry an excerpt, not a session pointer

The body must contain the actual reasoning — quoted or tightly paraphrased from the conversation — and never a reference that resolves elsewhere. "See the session where we discussed the exporter" is not resumable: transcripts get compacted, sessions end, and the reader is likely a different agent on a different machine with no access to yours. Quote the two or three exchanges that carry the argument, including the user's own words on anything subjective. **The excerpt travels with the seed; a pointer does not.**

For the same reason the harness's own `/fork` is not a substitute. A fork branches a *live* session; a cutting has to outlive the session entirely. Do not offer `/fork` in its place.

Excerpt, do not transcribe. A cutting is a distillation — enough to root, not the whole plant.

## Steps

1. **Bound the topic.** Confirm with the user what is being set aside, if more than one thread is in play. One cutting per topic; two topics parked at once are two seeds.

2. **Draft the body to a temp file.** A multi-paragraph body should not travel through argv:

       BODY=$(mktemp) && cat > "$BODY" <<'EOF'
       **What we were discussing:** …
       **Why it came up:** …
       **Established:** …
       **Open:** …
       EOF

3. **Create the seed, then attach the body.** `seeds create` takes the title; `seeds update --content-file` reads the body from the file. This is safe immediately after creation — the replacement guard only fires on a seed that has accumulated deliberation:

       seeds create -t "<the topic, stated to stand alone>" --type exploration --tags cutting
       seeds update <id> --content-file "$BODY"

   Tag it `cutting` so parked topics are findable as a set. Pass `--parent <id>` when the topic belongs under an existing deliberation, and `--type` whatever fits — `question` if the thing parked really is an open question.

4. **Confirm and hand it back.** Show the user the seed ID and title in one line, delete the temp file, and **return to the thread you were on.** Taking a cutting is not an instruction to start working it.
