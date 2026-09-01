---
id: seeds-176.6
title: Code is a concrete specification — the journey is deciding what goes in the contract
status: captured
type: idea
parent: seeds-176
created_at: 2026-06-18T22:31:09.519205+00:00
updated_at: 2026-08-31T20:02:44.399840+00:00
tags:
  - blog
  - journey
  - code-as-specification
  - contract
  - natural-language-dev
  - architect
  - next-post
relationships:
  - target_id: seeds-168
    rel_type: relates-to
    created_at: 2026-06-18T22:32:21.803480+00:00
  - target_id: seeds-176.5
    rel_type: relates-to
    created_at: 2026-06-18T22:32:21.915939+00:00
  - target_id: seeds-176.7
    rel_type: relates-to
    created_at: 2026-06-18T22:32:22.032852+00:00
  - target_id: seeds-179
    rel_type: questioned-by
    created_at: 2026-06-18T22:32:22.815139+00:00
converted_at: 2026-09-01T05:20:22.746832+00:00
---

A frame that crystallized while drafting the journey post (@aguynamedryan, stream-of-consciousness, verbatim-ish):

"Writing code is just writing a very specific specification. It's a contract between the human and the computer as to how the computer is expected to behave." Nobody wants to write that boilerplate contract — well, some people do; @aguynamedryan doesn't — "and it's beautifully cheap to do so now" (GenAI writes it). So the real question is "what are we wanting to put into that contract — what decisions? And for me, what ideas and deliberation went into what goes into that contract."

The merit is in going through THAT part of the journey — the planning that determines the contract's contents — not the writing of the contract itself. 25 years of programming trained @aguynamedryan's brain to do that planning to generate "the most effective systems, regardless of who's writing out the boilerplate contract." When AI arrived he did NOT want to handwrite specifications (he wants to move fast too); he surrendered the writing of code to GenAI — something he used to take pleasure in — and traded it for building more things, more quickly.

NATURAL-LANGUAGE-DEV TENSION (connects): code is "just a language that is a compromise for humans and for computers" — it must be understandable by both, so we meet in the middle and invent programming languages to describe these contracts/specifications. A year to a year-and-a-half ago, to get implementation from AI that met your needs, "you needed to practically specify the system in a very precise way to the point where you almost needed code" — i.e., the precise spec WAS approaching code. Code is the maximally-concrete end of the specification spectrum; seeds sits at the other end (what should the contract say, and why).

HOW THIS RELATES TO THE LANDSCAPE: DeltaDB and intent.build's Capture live AT the concrete contract — the conversation around writing/editing the code. seeds lives a level up: the deliberation about what the contract should contain and why. "Code is the centerpiece" tools optimize the contract; seeds optimizes the decision about the contract's contents.

OPEN QUESTION (attached as a question-seed): is "code is just a concrete specification / a human<->computer contract" a commonly-held view of software development? @aguynamedryan is sure someone articulates this; worth finding a citation to anchor the frame.

Related: seeds-176.7 (the journey IS the design process), seeds-168 (upstream-of-intent), seeds-176.5 (intent.build).
