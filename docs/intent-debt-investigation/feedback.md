# Feedback on the Intent-Debt Investigation

> Ryan's response to the analysis documents in this directory — [`capturing-the-why-landscape.md`](capturing-the-why-landscape.md), [`capturing-the-why-seeds-evaluation.md`](capturing-the-why-seeds-evaluation.md), [`seeds-gap-analysis.md`](seeds-gap-analysis.md), and [`proposed-seeds-for-seeds.md`](proposed-seeds-for-seeds.md). Dictated 2026-06-15 and lightly edited for readability; the positions and the hedges are preserved as given. This is a reader's reaction, not a set of decisions — some of it is firm, some of it is me noticing things about my own usage that I hadn't noticed before. Where I'm unsure, I've left the uncertainty in on purpose.

---

## 1. The headline: intent is the wrong unit — deliberation is upstream of it

My overall feeling, after three of these articles, is that **intent is too late in the pipeline for the thing I'm actually trying to capture.** The landscape and the evaluation are pretty good at capturing intent — that's not the problem. The problem is that intent, for me, is a *byproduct*. It's baked into deliberation and explored in deliberation. You don't figure out what you're trying to do until you've talked about and deliberated what you're trying to do. There's a whole conversation that goes into *determining* intent, and that conversation is the part I care about.

So when the evaluation gets excited about the "genuinely new from the landscape" — and specifically the **Triple Debt / "intent debt" vocabulary** — I'm more down on it than the document is. I'll nitpick the word. "Intent" sits further to the right than what we're capturing — further downstream, more settled. The intent-debt framing captures *the information that describes what you actually want*: what you've decided a product or a system should do, and why you wanted it to do that. That's totally great, and it's close to what seeds does. But it does **not** capture **what was considered and discarded along the way.** And that, to me, is the really important part.

Here's why the discarded path matters more than the destination:

- I hate going back and revisiting an old idea thinking it's a *new* idea.
- I hate coming up with an idea, thinking it's great, and not realizing I already dismissed it.
- And even when I do realize I dismissed it — *why* did I dismiss it? That doesn't show up in "intent" at all.

The value, concretely, is understanding **why decisions changed.** Why did a guard clause get put in, and why did it later get taken back out? What happened in the 2023 incident that changed hearts and minds — and what *other* resolutions to that incident were considered and rejected? None of that is intent. Intent is the residue after all of that has been resolved away. Deliberation is the only place the rejected branches survive.

One more thing that's been tickling me, and it cuts against my own framing a little: I want to say intent doesn't stray into design — but that's not true. I can hold an intent while the *way* I go about making it happen stays wide open. My intention with seeds is "capture deliberation." But the way I've actually gone about that is a long series of other decisions that aren't themselves that intent — and each one of *those* decisions has its own intent underneath it. So intent is fractal, and the deliberation is where each layer of it gets worked out. I *hope* seeds captures that adequately. I'm not certain it does.

On Addy Osmani's "pay it down" section specifically: the strategies there are all still anemic when it comes to capturing well-formed intent. They're competent at the destination and silent on the road.

---

## 2. Where seeds fits, in my own words

A few things I actually like, separate from the critique above:

- **It brings externalized artifacts into the repo itself.** One of the things I like about seeds is that the deliberation lands *in the repo*, captured directly alongside the code, instead of living in some external system that drifts away from the work.
- **"Review the intent, not the code" is already how I work.** The landscape treats this as an upstream-shifting prediction. For me, through seeds, it's just been the working reality — I'm steering at the level of the deliberation, not auditing generated diffs.
- **It's second-brain work, and I'm fine with that.** I'll defend this more under tension #9, but the short version: the hope was always that I could put *any* crazy idea into the system and trust it's locked away and available later, and that as I explore an idea, the exploration isn't lost either. That's a second brain. I think having one is important, and I want to see how far a very specific second brain can go.
- **It's not a panacea, and I know who it's for.** I'm not building crazy complicated systems. But if you're a solo dev with an AI partner and a client, trying to capture what you're thinking about the system you're building — seeds is a pretty good candidate for that. I won't claim more than that.

One honest uncertainty up front: **I can't speak to longevity.** seeds is five months old. We have no real evidence about whether it works *over years*. I'm operating on the assumption that it'll keep being handy, but that's an assumption, not a finding.

---

## 3. On the ten cross-cutting tensions (Part III of the landscape)

The landscape closes with ten tensions "worth watching." Going through them in order, because most of them land directly on how I actually use this:

**1. The capture↔intent spectrum.** seeds provides *both* — raw capture *and* distillation. It's not parked at one slice of the spectrum; it does some of the moving-rightward itself.

**2. Distillation is the field's unsolved problem.** I agree raw capture is not useful intent. What I can't tell yet is how much distillation you can cram into something like seeds *without losing the journey*, and conversely how much journey you can keep *without* drowning the system in noise. So far seeds seems to be walking that line acceptably for me — but "acceptably, for me, so far" is the honest ceiling on that claim.

**3. Upfront intent vs. emergent intent.** Both camps are right, and seeds should be *both worlds* — intent is prescribed *and* harvested. You have to have some idea of what you want before you start; you can't know everything you'll hit along the way. I fully agree with Dijkstra that knowing the spec ahead of time is impractical, and with Thorsten Ball that *building new software is learning* — which is exactly why deliberation matters: it captures the original approach, but also where approaches failed, why they were abandoned or changed, why there were pivots and re-evaluations, and the discoveries and insights gained en route.

   The gardening metaphor actually holds here. We *plant* the seed — that's the prescriptive part. We have an idea, we talk about it in the abstract, we explore the feasibility of applying it to the system, and we get into concrete notions of what that application should look like. All of that is easily and appropriately captured in seeds.

   **But here's where I'm weak, and the document caught me on it:** once the idea has been *tried*, what did we learn? Honestly — **I'm not capturing learning as much as I'd like.** That's a genuinely interesting gap. It's not impossible; part of why it hasn't happened is that by the time we reach implementation I've usually already got a firm handle on what I want, and a lot of the learning came from the *deliberation* itself rather than from the build. I don't have many examples of needing to revisit an implementation decision, because so far we've stood by the decisions we made — they've proven correct enough not to need revisiting. I'm not claiming we make perfect software. We'll see how that plays out. (This is the same nerve the gap analysis hits with "retrospective outcome" — Gap 4 / proposed seed 4. It's a real soft spot.)

**4. Capture-at-source vs. reconstruct-after.** I don't think reconstructing intent from residue is going to be very helpful. I've applied seeds to a decades-old system, but the one thing I have *not* asked it to do is go back and infer the decisions made before seeds existed. My assumption is that that information is lost to time — those deliberations are almost completely gone, and even the artifacts we do have (GitHub issues, documents, maybe a few emails) don't capture with anything like the rigor of a transcribed meeting. We don't store reconstructions and we don't infer intent from code or git commits; we infer intent only from *explicitly stated ideas*. It hasn't been necessary. seeds is a tool for a brave new world in which **discussion capture is cheap and easy** — and that's what it sources to capture deliberation. (So I'm cooler on the Meta-style "proactive corpus extraction" idea — gap analysis Gap 5 / proposed seed 5 — than the document is. Reconstruction-from-residue is a different and weaker thing than capture-at-source.)

**5. The candor paradox / observer effect.** This one mostly *doesn't apply to my environment*, and that's worth saying clearly. For the kind of work I do, **there are no hallways.** My conversations are always either directly with an AI for collaboration, or in a Zoom meeting for collaboration. Occasionally a Slack message carries some deliberation, and when it does I can just copy-paste those few errant messages into Claude and have it ingested into seeds. Everything is on the record — and my boss and I are *intentionally* seeking that out. When we discovered we could do AI transcription, we started transcribing everything, because that is exactly what we wanted. We're happy to talk about our decisions and we *want* them recorded. So the chilling effect the recording-firehose literature worries about isn't the environment seeds lives in for me. (That's a partial answer to Gap 2 / proposed seed 2 — the candor paradox is real in general, but it doesn't bite my workflow.)

**6. Embedded-in-workflow vs. separate step.** I need to look into this one more. First reaction: you could argue **seeds *is* the workflow** — it's the start of implementing new features, not a separate documentation chore bolted onto the side.

**7. Structure vs. natural language.** seeds captures a middle ground, and I think it's the right one. I believe ideas are interrelated, *and* I believe they're independent of each other to some extent. Inside a single seed it's just a giant natural-language blob — but we also say a seed *may be related* to other ideas. So we get free-form thought within the node and light structure between nodes. I think we're walking an okay line there. (This is my answer to the Kellogg "structure fights the model" challenge — Gap 3 / proposed seed 3. I don't feel the structure fighting me, because the structure is thin and lives mostly *between* seeds, not *inside* them.)

**8. Who is the audience now?** I genuinely don't know. I think the audience is still a human — but I never read seeds *directly*. My AI reads seeds for me and presents a cohesive picture of whatever we've captured. My mental image is: five years from now I come along and ask "why did we use SQLite as the backing database?" or "why did we explicitly export everything into a JSONL file?" — and the agent reconstructs that for me from the deliberation. I don't actually know that I care whether *the agent itself* knows those things, because that's not how I use agents right now. Right now I dole out very explicit sets of beads to implement, and **my goal is that an agent should never have to figure out what it's supposed to do — that should be solved before the agent is told to implement.** Which leads straight into my biggest open question (see §4).

**9. Capture as avoidance.** Absolutely not. My entire purpose is to capture *in order to implement* — to capture the deliberation in order to reach resolution, and to make that as frictionless and as fast as possible. To be cutesy: "capture is avoidance" is true only in the sense that what I'm avoiding is *forgetting an idea*, or feeling obligated to fully pursue an idea the moment I have it. The whole point is that I can drop any half-formed thought in and trust it's locked away and available, and that the later exploration isn't lost either. That's not procrastination dressed as productivity — it's second-brain work, and I'm okay with second-brain work. The files.md test is "does the tool make thinking *happen*, or just make not-thinking feel organized?" For me the answer is clear: **the tool makes thinking happen.**

   This also connects to something I value that the literature doesn't really name: seeds lets me **gauge my own cognitive capacity in the moment.** There are times I'm too tired to take on the entirety of what a feature needs from me cognitively. The choice in front of me becomes: do I break this feature into smaller parts my brain can handle right now, or do I *defer* the conversation to another time? And what I keep finding is that I end up *more* focused through a seeds interaction — my brain doesn't drift outside what's helpful, and when it does stray, I note the straying thought and return to the main thread faster. Even when I'm focused on a narrow slice of the system, I have the feeling that an agent using seeds still has access to the overarching ideas. That was part of the original hope: break deliberation about features into small manageable chunks the same way we break *code* into small manageable chunks — and postpone the heavy cognitive work not *indefinitely* (which would be the failure mode files.md warns about) but **until necessary.** That "until necessary" is the whole distinction.

**10. The McLuhan retrieval.** I don't actually know what this one is getting at yet. Flagging it to look at later, not responding.

---

## 4. The honest gaps, and what I should actually look into

Pulling the soft spots out of the above so they don't get lost in the prose:

- **Do agents actually consume seeds? I don't know, and I should find out.** The landscape keeps emphasizing intent-as-context-for-an-agent, and that has *not* been a focus of mine. I honestly don't know whether seeds has been providing context to agents when I ask them to implement something. We may want to go back and check: **(a)** do the beads even *reference* the seeds they came from? **(b)** when a seed is turned into beads, is the intent inside the seed actually *carried into* the bead? and **(c)** in the implementation session logs, is an agent ever actually *following* a reference back to a seed? I haven't looked, because I've been one-shotting features and haven't felt the need to look under the hood at whatever's causing the magic. But this is the most concrete, checkable open question to come out of reading these — and it's the thing that would tell me whether the "audience is the agent" framing is real for me or not. *(Action item, not a decision.)*

- **Learning capture is thinner than I'd like.** Restating from tension #3 because it surprised me: seeds is strong on the prescriptive plant-and-explore phase and weak on capturing what we *learned* after an idea was tried. Some of that is structural (I tend to have resolved my uncertainty by implementation time), but "I'm not capturing learning as much as I would like" is the most candid thing I noticed about my own usage.

- **Longevity is unproven.** Five months in. Everything above is "true so far."

---

## 5. Net read

The field spent early 2026 arriving at a premise I was already operating on, and that's validating. But I'd push back on letting its *vocabulary* set the terms. "Intent" is the settled output; **deliberation — including the branches we cut — is the upstream thing seeds is really for.** The evaluation is right that distillation-without-flattening and capture-in-the-moment are the hard open problems, and it's right that I've largely guarded against the drift risks (no ADR-style conclusion-output, no spec-authoring). The two things it *didn't* push hard enough on, from where I sit, are the ones I'd actually chase: whether the captured intent is genuinely reaching the agents that implement, and whether I'm capturing *learning* and not just *decisions*. Everything else I'm comfortable with — including the parts of the landscape (the candor paradox, reconstruct-from-residue) that simply don't describe the world I work in.
