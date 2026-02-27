# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-02-27

Initial public beta release.

### Added

- **Seed lifecycle**: captured → exploring → resolved/abandoned/deferred
- **Quick capture**: `seeds jot` for minimal-friction idea capture
- **Hierarchical seeds**: parent/child organization with dotted IDs (e.g., `seed-a1b2.1`)
- **Blocking semantics**: seeds with unresolved children cannot be resolved
- **Attached questions**: first-class question objects with open/answered/deferred lifecycle
- **Tagging**: comma-separated tags with filtering support
- **Relationships**: bidirectional `seeds link` for loose coupling between seeds
- **JSONL export**: git-trackable export via `seeds sync --flush-only`
- **AI context**: `seeds prime` command for agent workflow injection
- **Navigation commands**: `seeds ready`, `seeds blocked`, `seeds deferred`, `seeds questions`
- **Experimental web UI**: `seeds serve` for read-only browsing of seeds and questions
- **Doctor command**: `seeds doctor` for installation health checks
