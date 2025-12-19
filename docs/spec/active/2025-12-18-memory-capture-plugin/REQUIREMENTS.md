---
document_type: requirements
project_id: SPEC-2025-12-18-001
version: 1.0.0
last_updated: 2025-12-18T00:00:00Z
status: draft
---

# Memory Capture Plugin - Product Requirements Document

## Executive Summary

Extract the memory capture system from claude-spec into a fully independent, hybrid Python library + Claude Code plugin. The plugin provides Git-native, semantically-searchable context storage with feature parity to the original claude-spec implementation while supporting configurable namespaces, XDG-compliant storage, and pluggable embedding backends.

## Problem Statement

### The Problem

The memory capture system in claude-spec is tightly coupled to the spec planning workflow. Users who want Git-native semantic memory without the full claude-spec architecture planning features cannot access this capability independently.

### Impact

- Developers working on non-spec projects cannot benefit from persistent, searchable memory
- Teams who only need memory capture must install the entire claude-spec plugin
- The memory system cannot be used in other Claude Code workflows or plugins
- Knowledge captured in one workflow cannot easily transfer to others

### Current State

The memory system exists within `~/Projects/zircote/claude-spec/memory/` as 13 tightly-integrated Python modules (~2500 LOC) with dependencies on claude-spec-specific paths, configurations, and conventions.

## Goals and Success Criteria

### Primary Goal

Create a standalone, fully-featured memory capture plugin that provides all capabilities of the claude-spec memory system while being completely independent and configurable.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Feature parity | 100% | All 13 modules extracted with equivalent functionality |
| Test coverage | ≥90% | pytest-cov report |
| Independence | 0 claude-spec imports | Static analysis |
| Performance | ≤500ms capture, ≤200ms recall | Benchmark tests |
| Documentation | Complete | All public APIs documented |

### Non-Goals (Explicit Exclusions)

- Integration with claude-spec's `/cs:p`, `/cs:i`, `/cs:c` commands
- Spec-specific features (PROGRESS.md tracking, retrospective generation)
- Backward compatibility with claude-spec's internal data structures
- Migration tools for existing claude-spec memories (future enhancement)

## User Analysis

### Primary Users

| User Type | Description | Primary Needs |
|-----------|-------------|---------------|
| Claude Code Users | Developers using Claude Code for daily work | Persistent context across sessions |
| Plugin Authors | Developers building Claude Code plugins | Memory infrastructure for their plugins |
| AI Workflow Builders | Teams building AI-assisted workflows | Searchable knowledge base |

### User Stories

1. **As a Claude Code user**, I want to capture important decisions during my coding sessions so that I can recall them later without searching through conversation history.

2. **As a plugin author**, I want a memory library I can depend on so that my plugin can persist and recall context without reinventing storage.

3. **As a team lead**, I want captured memories to sync via git so that team members share institutional knowledge.

4. **As a developer**, I want to search my past learnings semantically so that similar problems surface relevant solutions.

5. **As a Claude Code user**, I want my memories organized by type (decisions, blockers, learnings) so that I can filter for what I need.

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | Capture memories to git notes | Core persistence mechanism | Memory persists after git push/pull |
| FR-002 | Semantic search via embeddings | Core retrieval mechanism | Query returns relevant memories by similarity |
| FR-003 | 10 memory namespaces | Feature parity | All namespaces: inception, elicitation, research, decisions, progress, blockers, reviews, learnings, retrospective, patterns |
| FR-004 | SQLite + sqlite-vec index | Fast search | KNN search returns in <200ms |
| FR-005 | Progressive hydration | Performance optimization | SUMMARY → FULL → FILES levels supported |
| FR-006 | Concurrent-safe capture | Multi-session support | File locking prevents corruption |
| FR-007 | YAML front matter format | Structured metadata | All memories have type, spec, timestamp, summary, tags |
| FR-008 | `/remember` command | User capture interface | Captures with namespace, summary, content |
| FR-009 | `/recall` command | User retrieval interface | Semantic search with filters |
| FR-010 | `/context` command | Bulk loading | Load all memories for a spec/project |
| FR-011 | `/memory status` command | Index inspection | Shows stats, health, recent captures |
| FR-012 | `/memory reindex` command | Index recovery | Rebuild index from git notes |
| FR-013 | Configurable git namespace | Conflict avoidance | Default: refs/notes/mem/*, user-configurable |
| FR-014 | XDG-compliant storage | Standard paths | ~/.local/share/memory-plugin/ default |
| FR-015 | Python library distribution | Reusability | pip install git-notes-memory works |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Pattern detection | Knowledge synthesis | Auto-detect success/anti-patterns |
| FR-102 | Memory lifecycle management | Relevance decay | Temporal decay with configurable half-life |
| FR-103 | `/memory verify` command | Consistency checking | Detect index vs git notes drift |
| FR-104 | `/memory gc` command | Cleanup | Remove tombstoned memories |
| FR-105 | Pluggable embedding backends | Flexibility | Support multiple sentence-transformer models |
| FR-106 | Query expansion | Better recall | Synonym expansion for searches |
| FR-107 | Result re-ranking | Relevance tuning | Recency boost, namespace priority |
| FR-108 | Prompt capture hook | Auto-capture | Optional UserPromptSubmit hook |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | `/memory export` command | Portability | Export to JSON/markdown |
| FR-202 | Web UI for browsing | Visibility | Local server showing memories |
| FR-203 | Cross-repo memory sharing | Team knowledge | Query memories from multiple repos |
| FR-204 | LLM-based summarization | Compression | Auto-summarize old memories |
| FR-205 | Memory migration tool | Adoption | Import from claude-spec notes |

## Non-Functional Requirements

### Performance

| Requirement | Target |
|-------------|--------|
| Capture latency | ≤500ms (including embedding generation) |
| Search latency | ≤200ms for top-10 results |
| Hydration (SUMMARY) | ≤10ms |
| Hydration (FULL) | ≤50ms per memory |
| Hydration (FILES) | ≤100ms per memory (20 file limit) |
| Index size | ≤10MB per 1000 memories |

### Security

- **SEC-001**: File locking (fcntl.flock) for concurrent access
- **SEC-002**: Git ref validation to prevent command injection
- **SEC-003**: Path validation to prevent directory traversal
- **SEC-004**: Content length limits (100KB max)
- **SEC-005**: No secrets in memory content (user responsibility + warnings)

### Scalability

- Support 10,000+ memories per repository
- Embedding model loaded lazily on first use
- Search cache with 5-minute TTL, 100-entry limit
- Batch operations for N+1 prevention

### Reliability

- Git notes are source of truth (index is derived)
- Index can be fully rebuilt from notes (`/memory reindex --full`)
- Graceful degradation if embedding fails (capture still succeeds)
- All operations idempotent where possible

### Maintainability

- 100% type-annotated (mypy strict)
- Docstrings on all public APIs
- Exception hierarchy with recovery actions
- Comprehensive test suite (unit + integration)

## Technical Constraints

### Python Environment

- Python 3.11+ required
- Dependencies: pyyaml, sentence-transformers, sqlite-vec
- Optional: numpy (for custom embeddings)

### Git Environment

- Git 2.25+ required (for notes features)
- Repository must be initialized
- User must have write access

### Claude Code Environment

- Claude Code CLI installed
- Plugin installed via marketplace or local install
- Skills and commands registered via plugin.json

## Dependencies

### Internal Dependencies

None - fully standalone.

### External Dependencies

| Dependency | Version | Purpose | License |
|------------|---------|---------|---------|
| pyyaml | ≥6.0 | YAML parsing | MIT |
| sentence-transformers | ≥2.2.0 | Embeddings | Apache 2.0 |
| sqlite-vec | ≥0.1.1 | Vector search | MIT |
| ruff | (dev) | Linting | MIT |
| mypy | (dev) | Type checking | MIT |
| pytest | (dev) | Testing | MIT |
| pytest-cov | (dev) | Coverage | MIT |

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Embedding model download fails on first use | Medium | High | Bundle small default model, clear error message |
| Git notes conflict with existing refs/notes/* | Low | Medium | Configurable namespace, conflict detection |
| sqlite-vec unavailable on some platforms | Low | High | Fallback to brute-force search, document requirements |
| Large memories exceed git note limits | Low | Medium | Content truncation with warning, split across notes |
| Breaking changes in sentence-transformers | Medium | Medium | Pin version range, test on CI |

## Open Questions

- [x] Git namespace: configurable (default refs/notes/mem/*)
- [x] Storage location: XDG compliant (~/.local/share/memory-plugin/)
- [x] Prompt hook: optional, disabled by default
- [x] Embedding model: pluggable, default all-MiniLM-L6-v2
- [ ] Package name: `git-notes-memory` or `memory-capture`?
- [ ] Plugin name: `memory-plugin` or `git-memory`?

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Git notes | Git's built-in mechanism for attaching metadata to commits |
| Namespace | Category of memory (decisions, learnings, etc.) |
| Hydration | Progressive loading of memory content from summary to full |
| Embedding | Vector representation of text for semantic search |
| sqlite-vec | SQLite extension for vector similarity search |

### References

- [claude-spec memory system](~/Projects/zircote/claude-spec/memory/)
- [Claude Code Plugins Guide](https://code.claude.com/docs/en/plugins)
- [Git Notes Documentation](https://git-scm.com/docs/git-notes)
- [sentence-transformers](https://www.sbert.net/)
- [sqlite-vec](https://github.com/asg017/sqlite-vec)
