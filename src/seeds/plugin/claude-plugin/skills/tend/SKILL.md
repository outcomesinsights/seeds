---
name: tend
description: Use when the user wants to review a related set of seeds and rule on them one topic at a time — "tend these seeds", "walk me through the seeds", "a seeds feedback session". Builds a queue of topics, shows each seed with full context and asks for its ruling through AskUserQuestion, and clears the session between topics (automatically inside herdr). `/seeds:tend next` continues the saved queue after a /clear.
---

# Tend a set of seeds

Tending takes existing seeds to rulings, one topic at a time. A **topic** is one seed plus the parent, child or related seeds that the user groups with it. Each topic gets its own cleared session, so one topic's context never crowds out the next. The rulings are in seed seeds-x6m0.

Tending is for a focused set: preparation before a few seeds are built, or a review of one cluster. It is never a review of the whole store. You tend a bed, not the garden.

The skill has two entry points:

- **`/seeds:tend [seed IDs or topic]`** starts a run. It builds the candidate list, shows the trim gate once, saves the queue, and presents the first topic.
- **`/seeds:tend next`** continues a run in a new session after a /clear. It reads the saved queue and presents the next topic. It shows no trim gate.

If the argument is exactly `next`, go to "Continue a run". Otherwise, go to "Start a run".

## The queue file

The queue lives in the per-worktree git directory, so git never tracks it and each worktree has its own:

```
"$(git rev-parse --absolute-git-dir)/seeds-tend-queue.md"
```

Outside a git repository, use `${XDG_STATE_HOME:-$HOME/.local/state}/seeds/tend/queue.md` instead.

Write it in this shape, so that a later session can read it with no other context:

```
# seeds:tend queue

Started: 2026-11-03 14:05
Scope: 7 seeds named in a discussion of the tend skill, plus 2 graph neighbors.

- [x] Topic 1: tend helper. seeds-z03u (the herdr helper that clears the session); seeds-x6m0 (the walkthrough format and rulings).
  Context: the user asked how the helper confirms a /clear.
- [ ] Topic 2: storage format. seeds-ab12 (one file per seed); seeds-ab12.1 (frontmatter keys).
  Context: the user said the frontmatter question blocks the release.
```

Each topic line gives every seed ID with a short gloss. The `Context:` line records what this conversation said about the topic. A /clear erases the conversation, so the `Context:` line is the only way that knowledge reaches a later session.

## Start a run

### 1. Check for an unfinished queue

If the queue file exists and has an open topic (`- [ ]`), say so. Ask the user whether to continue that queue or replace it. To continue, go to "Continue a run".

### 2. Build the candidate list from three tiers

Collect open seeds in this order of confidence. Do not use any other source.

1. **Named in this conversation.** Take every seed ID that appeared in this session, plus any seed IDs in the argument. The store cannot supply this tier, because it records what was written, not what was discussed.
2. **Graph neighbors, one hop.** Run `seeds tree <id>` for each tier-1 seed. Add its parent, its children and its related seeds.
3. **Topic search.** Run `seeds search '<regex for the discussion topic>'`. Use the argument as the topic if it is not a seed ID. `seeds search` leaves out resolved and abandoned seeds unless you pass `--all`, and tending needs open seeds only.

**`seeds recent` must not scope the set.** It sorts on writes, not on discussion, and tending itself writes, so it returns the seeds you just tended. It has one sanctioned use: the **cold open**. When the conversation named no seeds and the argument is empty, build the candidate list from `seeds recent` and `seeds ready`.

Drop resolved and abandoned seeds from every tier.

### 3. Show the trim gate, once

Show the candidates grouped by tier. Give each one its ID and a one-line gloss. Then propose a grouping into topics. Put a seed with its parent, children or related seeds when they share one decision.

Ask the user, with AskUserQuestion, to accept the proposed topics or to change them. The user can remove seeds, move seeds between topics and change the order. Apply the changes, and show the final queue in one short list.

This is the only trim gate. Later sessions do not repeat it.

### 4. Write the queue before anything else

Write the whole queue to the queue file now, before you present the first topic. The first /clear erases tier 1. A queue that is not on disk is lost.

Then go to "Present a topic" with the first open topic.

## Continue a run

Read the queue file. If it does not exist or has no open topic, say that no tend run is in progress, and stop. Suggest `/seeds:tend` to start one.

Otherwise, state the scope line and the position in one line, for example "Topic 2 of 4: storage format". Then go to "Present a topic" with the first open topic.

## Present a topic

Take the seeds of the topic one at a time. Present the parent before its children. For each seed:

### 1. Read before you write

Run `seeds show <id>` and `seeds questions --seed <id>`. Read the related seeds that the context block will cite. Check what shipped: read the commits and the code that the seed names. Do not change anything yet.

### 2. Write a prose context block

AskUserQuestion shows no context of its own, so the prose must do that work. Cover these points:

- What the seed proposed.
- Where the deliberation stands now.
- What shipped, with commit SHAs.
- What is stale.
- What is still unsettled.

Gloss every seed ID you mention with its title and why it matters here. The user does not recognize IDs.

### 3. Ask one AskUserQuestion call

Put the seed's open questions and its disposition into one call. A call holds up to four questions. The disposition options are:

- **Resolve** — the deliberation is complete.
- **Defer** — park it; it is not for now.
- **Abandon** — drop it.
- **Keep exploring** — leave it open.
- **Promote to a bead** — the seed is ready to build.

Chips carry the ruling. The prose and the notes field carry the reasoning. Do not turn a question whose answer is an argument into chips. Ask that question in prose, because four invented options would anchor the answer and lose the reasoning.

A preview on the disposition question can show the consequence of each option. For example, it can show which seeds become resolved, and which parent stays blocked. Only `resolved` and `abandoned` are terminal. One open child keeps its parent blocked, and a deferral does not change that.

### 4. Write the answers back, then move on

Write back before you present the next seed. Pass prose through a quoted heredoc (`<<'EOF'`), so that backticks in the text do not run as commands.

- **An answer to a question seed:** `seeds answer <question-id> "<answer>"`.
- **The reasoning:** `seeds update <id> --append -` with a note that starts `RULED YYYY-MM-DD:`.
- **Resolve:** `seeds resolve <id> -r "<what was decided>"`.
- **Defer:** append the reason first, then `seeds defer <id>`. `defer` takes no reason flag.
- **Abandon:** `seeds abandon <id> -r "<reason>"`.
- **Keep exploring:** `seeds explore <id>` if the seed is still `captured`.
- **Promote to a bead:** follow the seeds:seeds-to-beads skill for this seed.

Leave anything the user did not rule on untouched. "No answer yet" is a valid result, and the seed stays open.

## End a topic

When every seed in the topic has its ruling:

1. Mark the topic done in the queue file: change its `- [ ]` to `- [x]`.
2. If no open topic remains, say that the queue is finished. Delete the queue file, and stop.
3. Otherwise, ask with AskUserQuestion: **"Clear and continue"** or **"Stop"**. Name the next topic in the question.

### On "Stop"

Leave the queue file as it is. Tell the user that `/seeds:tend next` continues the run in any later session in this worktree.

### On "Clear and continue"

Run the helper that ships with this skill:

```
python3 "${CLAUDE_SKILL_DIR}/tend_clear.py"
```

The helper detaches and returns at once. It then waits until this pane is idle, sends `/clear`, confirms that the /clear took effect, and sends `/seeds:tend next`. It works only inside a herdr pane.

**Exit status 0.** The helper printed the path of its log. End your turn immediately with one short message, and make no more tool calls. The helper cannot send anything until this turn ends. Tell the user these three things:

- The session clears and the next topic starts when this turn ends.
- Do not type in the input box until the next topic appears, because the helper types into it.
- If nothing happens within a minute, type `/clear` and then `/seeds:tend next`. Give the log path.

**Any other exit status.** The session is not in herdr, or herdr or python3 is missing. The helper sent nothing. Tell the user to type `/clear`, and then `/seeds:tend next`.

Never send `/clear` or any other text to the pane yourself. The helper sends text only after the user picks "Clear and continue", because the user can have a draft in the input box.
