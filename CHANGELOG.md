# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-12-19

### Added

#### Core Services
- **CaptureService**: Memory capture with file locking for concurrency safety
  - `capture()` method with full metadata support
  - Namespace-specific convenience methods (capture_decision, capture_learning, etc.)
  - Batch capture support via `capture_batch()`

- **RecallService**: Memory retrieval with semantic search
  - `search()` for vector similarity search
  - `search_text()` for FTS5 keyword search
  - `get()`, `get_batch()`, `get_by_namespace()`, `get_by_spec()` retrieval methods
  - `proactive_recall()` for context-aware suggestions
  - Progressive hydration (SUMMARY, FULL, FILES levels)

- **SyncService**: Index synchronization with git notes
  - Full and incremental reindexing
  - Consistency verification and auto-repair
  - `collect_notes()` for gathering all notes

#### Storage Layer
- **IndexService**: SQLite + sqlite-vec for vector storage
  - 384-dimension sentence-transformer embeddings
  - KNN search with cosine similarity
  - FTS5 full-text search

- **GitOps**: Git operations wrapper
  - Git notes CRUD (add, show, remove)
  - Commit info retrieval
  - Sync configuration

- **EmbeddingService**: Sentence-transformer embeddings
  - Lazy model loading
  - 384-dimension vectors (all-MiniLM-L6-v2)
  - Batch embedding support

#### Advanced Features
- **SearchOptimizer**: Query expansion and result re-ranking
  - Synonym expansion
  - Reciprocal Rank Fusion (RRF) for combining results
  - LRU caching for repeated queries

- **PatternManager**: Cross-memory pattern detection
  - TF-IDF term analysis
  - Jaccard similarity clustering
  - Pattern lifecycle management (CANDIDATE → VALIDATED → PROMOTED)

- **LifecycleManager**: Memory aging and archival
  - Exponential decay for relevance scoring
  - Automatic state transitions (ACTIVE → RESOLVED → ARCHIVED → TOMBSTONE)
  - zlib compression for archived content
  - Garbage collection for old tombstones

#### Data Models
- 14 frozen dataclasses for immutability and thread-safety
- Core models: Memory, MemoryResult, HydratedMemory
- Result models: CaptureResult, CaptureAccumulator, IndexStats
- Pattern models: Pattern with PatternType and PatternStatus enums
- Git models: CommitInfo, NoteRecord

#### Configuration
- XDG-compliant data paths
- 10 memory namespaces (inception, elicitation, research, decisions, progress, blockers, reviews, learnings, retrospective, patterns)
- Environment variable overrides
- Configurable limits and timeouts

#### Utilities
- Temporal decay calculation for memory relevance
- ISO 8601 timestamp parsing
- Input validation (namespace, content size, git refs)

#### Claude Code Plugin
- Slash commands: /memory capture, /memory recall, /memory search, /memory sync, /memory status
- Memory recall skill for auto-context
- Optional prompt capture hook

### Security
- File locking with `fcntl` prevents concurrent corruption
- Git ref validation prevents shell injection
- Content size limits prevent DoS
- MD5 hashing marked as non-security (for content comparison only)

### Testing
- 910 tests with 93.65% coverage
- Unit tests for all modules
- Integration tests with real git repositories
- Security scanning with bandit
- Type checking with mypy (strict mode)

### Documentation
- User Guide with examples
- Developer Guide with full API reference
- README with quick start

[unreleased]: https://github.com/zircote/git-notes-memory/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/zircote/git-notes-memory/releases/tag/v0.1.0
