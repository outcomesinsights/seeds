# AI Planning/Design/Implementation Workflow Research

> Harvested 2026-03-11 from various blog posts, articles, and HN discussions.
> Purpose: Inform seeds design by understanding how people currently plan, deliberate, and track decisions when working with AI coding agents.

---

## Theme 1: Specification-First Development

Multiple practitioners describe a pattern where **planning documents precede implementation**, and those documents become the primary artifact — not the code.

- **project.md → plan.md flow**: "I start with a project.md file, where I describe what I want done. I then ask it to make a plan.md file from that project.md to describe the changes it will make." ([HN 47212355](https://news.ycombinator.com/item?id=47212355))

- **Layered documentation**: One practitioner uses three document types sequentially — design specs, phase-based plans, and debug logs. The agent iterates until the plan is "done." ([HN 47212355](https://news.ycombinator.com/item?id=47212355))

- **Research-informed architecture**: "Ask the agent to do research on the relevant subsystems and dump it to the change doc. This is to confirm that the agent correctly understands what the code is doing." ([HN 47212355](https://news.ycombinator.com/item?id=47212355))

- **Spec as unit of knowledge**: "A standardized Markdown specification [becomes] the new unit of knowledge for the software project… This specification, and not the code that materializes it, is what the team would need to understand, review, and be held accountable for." ([olano.dev](https://olano.dev/blog/dangerously-skip/))

- **Meta-planning**: Spending time with AI iterating on requirement documents before implementation. Engaging the AI to think through details, identify alternatives, and surface confusion until both parties thoroughly understand the spec. ([HN 47243272](https://news.ycombinator.com/item?id=47243272))

**Seeds relevance**: Seeds could serve as the deliberation layer that sits *above* specs. Where specs describe what to build, seeds capture the why, the alternatives considered, and the questions that need answering before a spec is ready.

---

## Theme 2: Deliberation Artifacts & Decision Tracking

People are recognizing that **AI-generated code obscures decision rationale** and they need new ways to capture reasoning.

- **Prompts as version-controlled context**: "We need to start saving prompts in version control. Prompts could be the context for both humans & machines." ([HN 47196582](https://news.ycombinator.com/item?id=47196582))

- **Reasoning compression problem**: "Compressed summaries that inform future sessions erase the original reasoning chains… you cannot audit the reasoning that produced it." ([ctolunchnyc](https://ctolunchnyc.substack.com/p/cracking-the-claw))

- **Deliberation tracking via markdown**: Rather than preserving full conversation transcripts, developers capture distilled artifacts — summarized requirements, architectural decisions, and rationale in markdown files committed alongside code. ([HN 47212355](https://news.ycombinator.com/item?id=47212355))

- **Agent traces as documentation**: "Successful AI agent work treats traces/logs as primary design documentation, not code artifacts alone." ([tomtunguz](https://tomtunguz.com/9-observations-using-ai-agents/))

- **Roadmap-driven brainstorming**: One developer maintains a roadmap and instructs the agent to "brainstorm implementation for the road map" before coding, creating checkpoints for deliberation. ([HN 47196582](https://news.ycombinator.com/item?id=47196582))

**Seeds relevance**: This is the core gap seeds addresses. The deliberation artifacts people are creating ad-hoc (markdown files, changelogs with prompts) are exactly what seeds could formalize with its lifecycle (captured → exploring → resolved) and question-tracking.

---

## Theme 3: Human Role Shifts to Curation & Judgment

With code generation becoming cheap, **the bottleneck moves to deciding what to build and evaluating what was built**.

- **Curation over creation**: "Success depends on curating and refining specs, saying yes or no to features, and taming unnecessary code." ([wesmckinney](https://wesmckinney.com/blog/mythical-agent-month/))

- **Design as constraint**: "Design, product scoping, and taste remain the practical constraints on delivering high quality software." ([wesmckinney](https://wesmckinney.com/blog/mythical-agent-month/))

- **Scope creep amplification**: Agents pursue "all avenues that would have previously been cost- or time-prohibitive," requiring disciplined decision-making to say "no." ([wesmckinney](https://wesmckinney.com/blog/mythical-agent-month/))

- **Conceptual integrity**: Maintaining a unified mental model of the system architecture becomes more critical, not less, as agents multiply output volume. ([wesmckinney](https://wesmckinney.com/blog/mythical-agent-month/))

- **Comprehension bottleneck**: "Reviewing PR feels even more implicit…tacit knowledge of context didn't form yet." The velocity of agent-generated code prevents slow knowledge accumulation. ([HN 47196582](https://news.ycombinator.com/item?id=47196582))

**Seeds relevance**: Seeds' lifecycle model (captured → exploring → deferred → resolved/abandoned) maps directly to this curation role. The "abandon" state is especially important — it's the explicit "no" that becomes harder to say when code is cheap.

---

## Theme 4: Experimental Prototyping Changes Cost-Benefit Thinking

When code is cheap to produce, **deliberation can shift from upfront analysis to experimental validation**.

- **Try it first**: "Any time our instinct says 'don't build that, it's not worth the time' fire off a prompt anyway, in an asynchronous agent session." ([simonwillison](https://simonwillison.net/guides/agentic-engineering-patterns/code-is-cheap/))

- **Cheap generation, expensive validation**: While generating code is cheap, ensuring it's good remains expensive. This creates a new deliberation challenge: determining which agent-generated work warrants refinement versus rejection. ([simonwillison](https://simonwillison.net/guides/agentic-engineering-patterns/code-is-cheap/))

- **Deliberate scoping**: Developers deliberately scope projects differently for personal tools vs. production software. The decision about which category something falls into is itself a deliberation moment. ([dbreunig](https://www.dbreunig.com/2026/02/25/two-things-i-believe-about-coding-agents.html))

- **Agents force earlier deliberation**: "Tasks with vague requirements…are now a bottleneck because when you type requirements to an agent for planning, [they] immediately surface various issues." Agents force earlier, more explicit deliberation. ([HN 47196582](https://news.ycombinator.com/item?id=47196582))

**Seeds relevance**: The "jot" command already supports this — low-friction capture of "what if we tried X?" But seeds could also support linking a seed to an experimental prototype, tracking the outcome of cheap experiments.

---

## Theme 5: Multi-Agent Deliberation & Oversight Patterns

People are developing structured patterns for how agents and humans interact during planning.

- **Multi-agent critique**: "Ask Claude to create a plan. Then prod Gemini & Codex to critique it; Claude addresses the critiques & implements the code." ([tomtunguz](https://tomtunguz.com/9-observations-using-ai-agents/))

- **Plan mode as foundation**: "Make sure the agent reviews the plan, ask the agent to make suggestions and ask questions" before execution begins. ([HN 47243272](https://news.ycombinator.com/item?id=47243272))

- **Graduated autonomy**: Start with low-risk outputs (comments, drafts, reports) before enabling pull request creation. Test assumptions before automating higher-stakes decisions. ([GitHub Blog](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/))

- **Trust evolution**: Beginners practice pre-approval (checking each step); experienced users shift to "active monitoring" — delegating work and intervening reactively. ([garryslist](https://garryslist.org/posts/half-the-ai-agent-market-is-one-category-the-rest-is-wide-open))

- **Workflows as living specs**: "Treat the workflow Markdown as code. Review changes, keep it small, and evolve it intentionally." ([GitHub Blog](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/))

**Seeds relevance**: Seeds could be the place where these multi-agent deliberation artifacts land. When you ask multiple models to critique a plan, the critiques and responses could be captured as questions and answers on a seed.

---

## Theme 6: Task Decomposition & Intentional Structure

Effective AI collaboration requires **breaking work into well-defined, observable units**.

- **47-task decomposition**: "What are the 47 things a developer does in a given week, and which of those can be amplified?" Map specific friction points before deploying AI assistance. ([kasava.dev](https://www.kasava.dev/blog/ai-as-exoskeleton))

- **Visible seams**: "Make the seams visible" — structure AI work with clear inputs/outputs for each component, enabling teams to identify exactly where breakdowns occur. ([kasava.dev](https://www.kasava.dev/blog/ai-as-exoskeleton))

- **Analysis vs. judgment separation**: "The AI goes deep. The human decides what matters." Create a clear deliberation workflow where research and judgment remain separated. ([kasava.dev](https://www.kasava.dev/blog/ai-as-exoskeleton))

- **Language choice as deliberation constraint**: Choosing Go over Rust to minimize context spent on "lifetimes, interpreting and fixing compiler warnings" — deliberate language choices based on LLM cognitive load. ([HN 47222270](https://news.ycombinator.com/item?id=47222270))

- **Anti-pattern**: Lightweight planning followed by code generation creates "local hill-climbing" where teams invest heavily in review but miss fundamentally better architectural approaches. ([HN 47243272](https://news.ycombinator.com/item?id=47243272))

**Seeds relevance**: Seeds' hierarchical structure (parent/child seeds) already supports decomposition. The "blocked" concept (can't resolve parent until children resolve) enforces this structure.

---

## Summary: What This Means for Seeds

The research reveals a clear gap in the AI-assisted development workflow: **people need better tools for the deliberation phase that sits between "I have an idea" and "here's the spec."**

Current ad-hoc approaches include:
1. Markdown files (project.md, plan.md, spec.md) manually managed
2. Prompt logs in version control
3. Agent conversation traces as documentation
4. Multi-agent review workflows with no formal artifact capture

Seeds is well-positioned to formalize this because it already has:
- Low-friction capture (`jot`)
- Lifecycle tracking (captured → exploring → resolved/abandoned)
- Question attachment and answer tracking
- Hierarchical decomposition
- Git-backed persistence

Potential areas to explore based on this research:
- **Link seeds to experiments**: When "code is cheap," seeds could track which ideas were prototyped and what the outcome was
- **Capture agent reasoning**: Seeds could store distilled reasoning from agent sessions, solving the "reasoning compression" problem
- **Multi-perspective deliberation**: Seeds could capture critiques from different agents/sources as first-class objects
- **Specification graduation**: A seed lifecycle could include a "spec-ready" state indicating deliberation is complete enough for implementation
