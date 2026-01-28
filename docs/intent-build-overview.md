# Intent.build — Complete Overview

> **The system of record for human decisions in software.**

*Last updated: January 27, 2026*

---

## TL;DR

Intent captures the **why** behind your code—from AI agent sessions to team discussions—and versions it alongside your codebase. Every decision linked to the code it produced. Searchable forever.

Works with: Claude Code, Cursor, Copilot, Codex, Gemini

---

## The Problem Intent Solves

Software moves faster than teams can keep up. AI agents have made execution cheap—code appears instantly. But the **reasoning behind that code** still lives in places that don't scale:

- Chat logs that disappear after 90 days
- Meeting notes lost in someone's folder
- Wikis that go stale because nobody updates them
- Documentation that drifts from reality
- People's heads (until they leave)

As development accelerates, critical context disappears faster. Teams spend more time **rediscovering conclusions** than building on them.

The result: code that looks right but crumbles under pressure because it was built without deep understanding of the whole.

---

## Philosophy

From their About page:

> "In the age of AI, the most important thing to preserve is human intent."

The bottleneck has moved. It's no longer about how fast we can type, but **how clearly we can think**. The new tools create mental tax—drowning us in micro-decisions about what context to give agents.

Intent's bet: **the craft isn't just about speed. It's about depth of thought.**

They're building tools that help you think, because that's where the real work now lies. Not one-click magic buttons, but infrastructure for "mindful making."

---

## How Intent Works

Three integrated surfaces:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Capture   │────▶│    Arena    │────▶│    Repo     │
│  (Record)   │     │(Collaborate)│     │   (Store)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Capture** → Automatically records decisions from AI coding tools  
**Arena** → Real-time collaboration with automatic decision extraction  
**Repo** → Decisions stored in `.intent/`, versioned with your code

---

## 1. Capture (The Input Layer)

Monitors your project and automatically extracts decisions from AI coding sessions—no manual documentation required.

### How It Works

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   File Watcher   │────▶│  Session Parser  │────▶│   Correlation    │
│   (filesystem)   │     │  (AI sessions)   │     │     Engine       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                    │
                                    ▼
                         ┌──────────────────┐
                         │  Decision Store  │
                         │   (journal.db)   │
                         └──────────────────┘
```

### Components

**File Watcher**
- Monitors all file changes in real-time (create, modify, delete, rename)
- 30-second reconciliation loop to catch missed events
- All changes written to journal as system of record

**Session Parser**
- Extracts structured data from AI tool sessions
- For Claude Code: monitors `~/.claude/projects/{project-path}/*.jsonl`
- Extracts: user prompts, agent replies, file operations, content hashes
- Understands 15+ file-editing tools, normalizes paths to project root

**Correlation Engine**
- Links filesystem changes to the AI exchanges that created them
- Matches on: file paths, content hashes, timing, operation type
- Creates **provenance**—trace any line of code back to its originating conversation

### Decision Enrichment

Once correlated, Intent generates AI enrichment for each exchange:

```json
{
  "title": "Implement JWT authentication middleware",
  "intent": "Add secure token-based authentication to protect API routes",
  "approach": "Used RS256 signing with refresh token rotation",
  "impact": "All /api routes now require valid JWT in Authorization header",
  "tags": ["authentication", "jwt", "security", "middleware"],
  "phase": "Authentication System",
  "complexity": "medium"
}
```

### Session Enrichment

Higher-level summary of entire coding sessions:

```json
{
  "scope": "Implemented complete JWT auth system with refresh tokens",
  "keyDecisions": [
    "Chose RS256 over HS256 for key rotation support",
    "Added 15-minute access token expiry with 7-day refresh"
  ],
  "challenges": "Handling token expiration edge cases during active requests",
  "technologies": ["Go", "JWT", "bcrypt", "middleware"],
  "outcomes": "Secure authentication with automatic token refresh"
}
```

### Provenance Mapping

Bi-directional navigation between code and conversation:

```
┌─────────────────────────────────────────────────────────────┐
│ src/auth/middleware.ts                                      │
├─────────────────────────────────────────────────────────────┤
│ Lines 1-15  ← Exchange ex_0_abc123: "Add JWT validation"    │
│ Lines 16-42 ← Exchange ex_0_def456: "Handle token refresh"  │
│ Lines 43-60 ← Exchange ex_0_ghi789: "Add error responses"   │
└─────────────────────────────────────────────────────────────┘
```

- **Code → Conversation:** Click any line to see the exchange that created it
- **Conversation → Code:** Click any exchange to highlight the lines it produced

### Supported Sources

| Source | What's Recorded |
|--------|-----------------|
| Claude Code | Full conversation sessions with tool calls, file operations |
| Cursor | Chat and Composer sessions with file operations |
| Codex CLI | Session capture with file operations |
| Gemini CLI | Session capture with file operations |
| Filesystem | All file CRUD operations with content hashes |

### Offline Support

Handles offline work gracefully:
- Creates baseline snapshot when daemon starts
- On restart, compares current filesystem to baseline
- Detects all changes that occurred while offline
- Identifies renames via content-hash matching
- No data lost, even after days offline

### Configuration

`.intent/config.json`:
```json
{
  "capture": {
    "watchPaths": ["."],
    "ignorePaths": ["node_modules", ".git", "dist"],
    "sessionIdleTimeout": 300
  }
}
```

Also supports `.intentignore` (same syntax as `.gitignore`).

---

## 2. Arena (The Collaboration Layer)

Real-time collaboration combining conversation, shared editing, and automatic decision extraction.

### Features

**Voice and Video**
- LiveKit integration for real-time communication
- Screen sharing for code walkthroughs
- Automatic transcription of everything said
- Transcription feeds into decision extraction

**Shared Editor**
- CodeMirror + Automerge powered
- Real-time co-editing with no conflicts
- CRDT-backed for offline tolerance
- Provenance tracking (who wrote what)

**Decision Extraction**
- AI monitors conversation in real-time
- Extracts: what was decided, why, who, when
- No more "what did we decide?" after the call

### Workflow

1. **Create session:** `intent arena create "API Architecture Discussion"`
2. **Join:** Team members join via shared link
3. **During session:**
   - Transcription captures everything
   - Editor changes tracked with attribution
   - Decisions appear in sidebar as identified
   - Can accept, edit, reject, or manually add decisions
4. **After session:**
   - Full transcript saved
   - Decisions finalized and linked to context
   - Everything syncs to Intent Repo
   - Becomes permanent, searchable artifact

### Use Cases

- **Architecture Reviews:** Discuss approaches, decisions captured as you talk
- **Pair Programming:** Real-time collaboration with attribution
- **Incident Response:** 2 AM debugging sessions captured for post-mortem
- **Onboarding:** Walkthrough sessions become reference material

### Privacy

- Private (invited only), Team, or Link-based access
- Encrypted in transit and at rest
- Configurable retention periods

---

## 3. Repo (The Storage Layer)

Decisions versioned alongside source code—consumable by humans and agents, diffable across releases, searchable forever.

### Directory Structure

```
.intent/
├── config.json           # Project configuration
├── episodes.db           # Episode metadata (SQLite)
├── active-episode        # Name of current episode
├── episodes/
│   └── main/             # Default episode
│       ├── db/
│       │   └── journal.db    # Event log with FTS index
│       └── crdt-storage/     # Per-file version history
├── state/                # Catchup snapshots
├── service.log           # Daemon logs
├── service.pid           # Process ID
└── service.sock          # Unix socket for RPC
```

**Commit this directory to version control** — your project's reasoning travels with your code.

### The Journal

`journal.db` is the system of record. Every event flows through it:

| Event Type | What It Records |
|------------|-----------------|
| `file_change` | File create, modify, delete, rename |
| `provenance_hint` | AI session file operation extraction |
| `decision_enrichment` | AI-generated exchange metadata |
| `session_enrichment` | AI-generated session summary |
| `correlation.match` | Link between file change and AI exchange |

SQLite with FTS5 full-text indexing enables instant search.

### CRDT Storage (Why Not Git-Style Diffs?)

| Git-style | CRDT-style |
|-----------|------------|
| Three-way merge required | Automatic conflict resolution |
| Merge conflicts possible | Merges are always clean |
| Centralized history | Distributed, offline-tolerant |
| Snapshot-based | Operation-based with attribution |

CRDTs enable:
- Offline work that syncs cleanly later
- Real-time collaboration without locks
- Per-character attribution
- Provenance marks

### Episodes (Like Git Branches, But for Decisions)

```bash
intent episode list                              # List episodes
intent episode create feature-auth              # Create new episode
intent episode switch feature-auth              # Switch to episode
intent episode diff main feature-auth           # Compare episodes
intent episode integrate feature-auth --mode llm  # Semantic merge
```

Each episode has its own journal, CRDT storage, and decision history.

The `--mode llm` option uses **semantic merging**—an LLM analyzes changes and produces a coherent merge, not just mechanical line-by-line diff.

### Search Capabilities

**Natural Language:**
```bash
intent ask "why did we choose PostgreSQL over MongoDB?"
```

**Interactive Shell:**
```bash
intent shell
# Supports: natural language, @ references, slash commands
```

**Direct Queries:**
```bash
intent timeline              # Recent decisions
intent history src/auth.ts   # File history
intent exchange ex_0_abc123  # Specific exchange
intent diff src/auth.ts@v3 src/auth.ts@v5
```

### Version History

```bash
$ intent history src/auth/middleware.ts

v5 2024-01-15 14:32 "Add token refresh logic"
   Exchange: ex_0_ghi789
   Intent: Handle expired tokens gracefully

v4 2024-01-15 14:28 "Add error responses"
   Exchange: ex_0_def456
   Intent: Return proper HTTP status codes
```

Restore previous versions:
```bash
intent show src/auth.ts@v3      # Preview
intent restore src/auth.ts@v3   # Restore
```

### Cloud Sync (Optional)

Local-first by default. Cloud sync provides:
- Team visibility
- Cross-device access
- Backup
- Arena integration

```bash
intent login
intent remote set https://sync.intent.build
intent web register
```

### Git Integration

Complements Git (what changed) with Intent (why).

```bash
intent commit ex_0_abc123          # Generate commit from exchange
intent export --format git-notes   # Export provenance
```

### Storage Efficiency

- Incremental snapshots
- Content deduplication
- FTS indexing
- Configurable retention

Typical: ~1-5 MB per month of active development.

---

## CLI Reference

### Initialization & Status

```bash
intent init                    # Initialize Intent in project
intent status                  # Daemon status and health
intent version                 # CLI version
```

### Configuration

```bash
intent configure llm           # Set Anthropic API key
intent configure slack         # Set up Slack notifications
```

### Search & Discovery

```bash
intent ask "query"             # Natural language search
intent shell                   # Interactive shell
intent timeline                # Decision timeline
```

### History & Versions

```bash
intent history [file]          # Browse version history
intent show <file>@<version>   # Display specific version
intent diff <file>@v1 <file>@v2  # Compare versions
intent restore <file>@v        # Restore previous version
```

### Exchanges & Sessions

```bash
intent exchange <id>           # Inspect exchange
intent sessions                # List recent AI sessions
```

### Episodes

```bash
intent episode list
intent episode create <name>
intent episode switch <name>
intent episode diff <ep1> <ep2>
intent episode integrate <src> --mode llm
```

### Service Management

```bash
intent service start
intent service stop
intent service restart
```

### Cloud & Sync

```bash
intent login
intent remote set <url>
intent web register
intent stream                  # Monitor sync activity
```

### Journal & Debugging

```bash
intent journal list --type decision_enrichment --limit 10
intent rebuild                 # Rebuild CRDT from journal
```

### Git Integration

```bash
intent commit <exchange-id>
intent export --format git-notes
```

---

## Pricing

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | Capture, Repo |
| **Team** | From $35/user/month | + Arena, History, Admin controls |
| **Enterprise** | Custom | + SSO, audit logs |

Usage-based pricing for Arena sessions, transcription, and AI features.

Currently working with Early Design Partners.

---

## Key Takeaways

1. **Problem:** Critical context (decisions, tradeoffs, reasoning) disappears as development accelerates. Code appears fast; understanding doesn't.

2. **Solution:** Capture decisions where they happen (AI sessions, team discussions), turn them into durable artifacts, keep them connected to the code they produced.

3. **Philosophy:** "Mindful making." The craft is about depth of thought, not just speed.

4. **Architecture:** Three layers—Capture (input), Arena (collaborate), Repo (store)—all feeding into the same decision format and search index.

5. **Local-first:** Your data stays in `.intent/` in your project. Cloud sync optional.

6. **Provenance:** Bi-directional links between code and the conversations that created it.

7. **CRDTs over Git-diffs:** Automatic conflict resolution, offline-tolerant, per-character attribution.

8. **Episodes:** Isolated workspaces with semantic (LLM-powered) merging.

9. **Integration:** Works with major AI coding tools (Claude Code, Cursor, Copilot, Codex, Gemini). Complements Git.

10. **Search:** Natural language queries via Claude, interactive shell, direct journal queries.

---

## Links

- **Website:** https://intent.build
- **Docs:** https://www.intent.build/docs
- **Early Access:** https://www.intent.build/design-partner

---

*Document generated by Molto 🦞 for Ryan Duryea*
