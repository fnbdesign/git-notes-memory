---
document_type: implementation_plan
project_id: SPEC-2025-12-18-001
version: 1.0.0
last_updated: 2025-12-18T00:00:00Z
status: draft
estimated_effort: 5-7 days
---

# Memory Capture Plugin - Implementation Plan

## Overview

Extract the memory capture system from claude-spec into a standalone Python library + Claude Code plugin. The implementation follows a phased approach, starting with core infrastructure, then services, then integration layers.

## Phase Summary

| Phase | Focus | Key Deliverables |
|-------|-------|------------------|
| Phase 1: Foundation | Project scaffold, models, config | Python package structure, all data models, configuration system |
| Phase 2: Storage Layer | Git operations, index, embedding | GitOps, IndexService, EmbeddingService |
| Phase 3: Core Services | Capture and recall | CaptureService, RecallService, SyncService |
| Phase 4: Advanced Features | Search, patterns, lifecycle | SearchOptimizer, PatternManager, LifecycleManager |
| Phase 5: Plugin Integration | Claude Code plugin | Commands, skills, hooks |
| Phase 6: Polish & Release | Testing, docs, distribution | Tests, documentation, PyPI/GitHub release |

---

## Phase 1: Foundation

**Goal**: Establish project scaffold with all data models and configuration

### Task 1.1: Initialize Python Package Structure

- **Description**: Create the Python package skeleton with pyproject.toml, src layout, and test structure
- **Acceptance Criteria**:
  - [ ] `pyproject.toml` with correct metadata and dependencies
  - [ ] `src/git_notes_memory/` package structure
  - [ ] `tests/` directory structure
  - [ ] `.gitignore` for Python projects
  - [ ] `LICENSE` (MIT)
  - [ ] `README.md` placeholder

**Source Reference**: Adapt from `~/Projects/zircote/claude-spec/pyproject.toml`

### Task 1.2: Implement Data Models

- **Description**: Port all dataclasses from models.py with full type annotations
- **Files to Create**: `src/git_notes_memory/models.py`
- **Models to Implement**:
  - [ ] `Memory` - Core memory entity
  - [ ] `MemoryResult` - Memory with distance
  - [ ] `HydrationLevel` - Enum (SUMMARY, FULL, FILES)
  - [ ] `HydratedMemory` - Memory with full content and files
  - [ ] `SpecContext` - All memories for a spec
  - [ ] `IndexStats` - Index statistics
  - [ ] `VerificationResult` - Consistency check results
  - [ ] `CaptureResult` - Capture operation result
  - [ ] `CaptureAccumulator` - Session capture tracker
  - [ ] `Pattern` - Detected pattern
  - [ ] `CommitInfo` - Git commit metadata
  - [ ] `NoteRecord` - Parsed note record
- **Acceptance Criteria**:
  - [ ] All models are frozen dataclasses
  - [ ] Full type annotations with `from __future__ import annotations`
  - [ ] Docstrings on all classes
  - [ ] Unit tests for model creation and validation

**Source Reference**: `~/Projects/zircote/claude-spec/memory/models.py`

### Task 1.3: Implement Configuration System

- **Description**: Create config module with namespaces, paths, and settings
- **Files to Create**: `src/git_notes_memory/config.py`
- **Configuration Items**:
  - [ ] `NAMESPACES` - Set of 10 valid namespaces
  - [ ] `DEFAULT_GIT_NAMESPACE` - `refs/notes/mem`
  - [ ] `XDG_DATA_PATH` - `~/.local/share/memory-plugin/`
  - [ ] `INDEX_DB_NAME` - `index.db`
  - [ ] `MODELS_DIR` - `models/`
  - [ ] `LOCK_FILE` - `.capture.lock`
  - [ ] `DEFAULT_EMBEDDING_MODEL` - `all-MiniLM-L6-v2`
  - [ ] `EMBEDDING_DIMENSIONS` - 384
  - [ ] `MAX_CONTENT_BYTES` - 102400
  - [ ] `MAX_SUMMARY_CHARS` - 100
  - [ ] `MAX_HYDRATION_FILES` - 20
  - [ ] `MAX_FILE_SIZE` - 102400
  - [ ] `SEARCH_TIMEOUT_MS` - 500
  - [ ] `CAPTURE_TIMEOUT_MS` - 2000
  - [ ] `CACHE_TTL_SECONDS` - 300
  - [ ] `CACHE_MAX_ENTRIES` - 100
  - [ ] `DECAY_HALF_LIFE_DAYS` - 30
- **Environment Variables**:
  - [ ] `MEMORY_PLUGIN_GIT_NAMESPACE` - Override git namespace
  - [ ] `MEMORY_PLUGIN_DATA_DIR` - Override data directory
  - [ ] `MEMORY_PLUGIN_EMBEDDING_MODEL` - Override embedding model
  - [ ] `MEMORY_PLUGIN_AUTO_CAPTURE` - Enable/disable auto-capture
- **Acceptance Criteria**:
  - [ ] All constants documented
  - [ ] Environment variable overrides work
  - [ ] `get_data_path()`, `get_index_path()`, `get_models_path()` helpers
  - [ ] Unit tests for config resolution

**Source Reference**: `~/Projects/zircote/claude-spec/memory/config.py`

### Task 1.4: Implement Exception Hierarchy

- **Description**: Create custom exception classes with recovery actions
- **Files to Create**: `src/git_notes_memory/exceptions.py`
- **Exceptions to Implement**:
  - [ ] `MemoryError` - Base exception with category, message, recovery_action
  - [ ] `StorageError` - Git operations failures
  - [ ] `MemoryIndexError` - Database failures
  - [ ] `EmbeddingError` - Model loading/generation failures
  - [ ] `ParseError` - YAML/note format issues
  - [ ] `CaptureError` - Capture orchestration failures
  - [ ] `ValidationError` - Input validation failures
- **Acceptance Criteria**:
  - [ ] All exceptions have `category`, `message`, `recovery_action` attributes
  - [ ] Proper inheritance hierarchy
  - [ ] Unit tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/exceptions.py`

### Task 1.5: Implement Utility Functions

- **Description**: Port shared utilities for timestamps, decay, validation
- **Files to Create**: `src/git_notes_memory/utils.py`
- **Functions to Implement**:
  - [ ] `generate_memory_id()` - UUID generation
  - [ ] `calculate_decay(timestamp, half_life)` - Exponential decay
  - [ ] `validate_namespace(namespace)` - Check against valid set
  - [ ] `validate_git_ref(ref)` - Prevent command injection
  - [ ] `validate_path(path)` - Prevent traversal
  - [ ] `validate_content_length(content)` - Size limit check
  - [ ] `truncate_summary(text, max_chars)` - Safe truncation
  - [ ] `format_timestamp(dt)` - ISO 8601 formatting
  - [ ] `parse_timestamp(s)` - ISO 8601 parsing
- **Acceptance Criteria**:
  - [ ] All functions documented and typed
  - [ ] Unit tests with edge cases

**Source Reference**: `~/Projects/zircote/claude-spec/memory/utils.py`

### Task 1.6: Implement Note Parser

- **Description**: YAML front matter parsing for git notes
- **Files to Create**: `src/git_notes_memory/note_parser.py`
- **Functions to Implement**:
  - [ ] `parse_note(content)` - Extract front matter and body
  - [ ] `serialize_note(metadata, body)` - Create note string
  - [ ] `validate_front_matter(fm)` - Check required fields
- **Acceptance Criteria**:
  - [ ] Handles malformed YAML gracefully
  - [ ] Preserves body formatting
  - [ ] Unit tests with various note formats

**Source Reference**: `~/Projects/zircote/claude-spec/memory/note_parser.py`

### Phase 1 Deliverables

- [ ] Python package installable via `pip install -e .`
- [ ] All data models implemented and tested
- [ ] Configuration system with environment variable support
- [ ] Exception hierarchy with recovery actions
- [ ] Utility functions with validation

### Phase 1 Exit Criteria

- [ ] `pytest` passes for all Phase 1 tests
- [ ] `mypy --strict` passes
- [ ] `ruff check` passes

---

## Phase 2: Storage Layer

**Goal**: Implement the three storage backends: Git, SQLite, and Embeddings

### Task 2.1: Implement GitOps

- **Description**: Git command wrapper with validation
- **Files to Create**: `src/git_notes_memory/git_ops.py`
- **Methods to Implement**:
  - [ ] `add_note(commit, content, namespace)` - Add new note
  - [ ] `append_note(commit, content, namespace)` - Append to note
  - [ ] `show_note(commit, namespace)` - Get note content
  - [ ] `list_notes(namespace)` - List all notes
  - [ ] `remove_note(commit, namespace)` - Delete note
  - [ ] `get_commit_sha(ref)` - Resolve ref to SHA
  - [ ] `get_commit_info(sha)` - Get commit metadata
  - [ ] `get_file_at_commit(sha, path)` - Get file snapshot
  - [ ] `get_changed_files(sha)` - List modified files
  - [ ] `configure_sync(namespace)` - Auto-configure remote sync
  - [ ] `_run_git(args)` - Internal git command runner
- **Security**:
  - [ ] All refs validated via `validate_git_ref()`
  - [ ] All paths validated via `validate_path()`
  - [ ] Never use `shell=True`
- **Acceptance Criteria**:
  - [ ] All operations work in real git repos
  - [ ] Proper error handling for non-git directories
  - [ ] Unit tests with mocked subprocess

**Source Reference**: `~/Projects/zircote/claude-spec/memory/git_ops.py`

### Task 2.2: Implement IndexService

- **Description**: SQLite + sqlite-vec database management
- **Files to Create**: `src/git_notes_memory/index.py`
- **Methods to Implement**:
  - [ ] `initialize()` - Create schema if not exists
  - [ ] `insert(memory, embedding)` - Add memory + vector
  - [ ] `get(memory_id)` - Get by ID
  - [ ] `get_batch(memory_ids)` - Batch retrieval
  - [ ] `get_by_spec(spec)` - Get all for spec
  - [ ] `get_by_commit(sha)` - Get all for commit
  - [ ] `search_vector(embedding, limit, filters)` - KNN search
  - [ ] `update(memory_id, updates)` - Modify metadata
  - [ ] `delete(memory_id)` - Remove memory
  - [ ] `list_recent(limit, namespace)` - Recent memories
  - [ ] `get_stats()` - Index statistics
  - [ ] `verify()` - Consistency check
  - [ ] `close()` - Cleanup connection
- **Schema**:
  - [ ] `memories` table with all fields
  - [ ] `vec_memories` virtual table (sqlite-vec)
  - [ ] Indexes on spec, namespace, timestamp, commit, status
- **Acceptance Criteria**:
  - [ ] sqlite-vec extension loads correctly
  - [ ] KNN search returns correct results
  - [ ] Batch operations prevent N+1
  - [ ] Integration tests with real database

**Source Reference**: `~/Projects/zircote/claude-spec/memory/index.py`

### Task 2.3: Implement EmbeddingService

- **Description**: Sentence transformer embeddings with lazy loading
- **Files to Create**: `src/git_notes_memory/embedding.py`
- **Methods to Implement**:
  - [ ] `embed(text)` - Single text to vector
  - [ ] `embed_batch(texts)` - Multiple texts
  - [ ] `get_dimensions()` - Model dimension
  - [ ] `is_loaded()` - Model status
  - [ ] `unload()` - Free memory
  - [ ] `_load_model()` - Internal model loading
- **Configuration**:
  - [ ] Configurable model via env var
  - [ ] Model cache in XDG data directory
- **Error Handling**:
  - [ ] Network errors → clear message
  - [ ] Out of memory → graceful error
  - [ ] Model corruption → redownload
- **Acceptance Criteria**:
  - [ ] Lazy loading works (first call loads model)
  - [ ] 384-dimension vectors for default model
  - [ ] Model cached to correct directory
  - [ ] Integration tests (may be slow)

**Source Reference**: `~/Projects/zircote/claude-spec/memory/embedding.py`

### Phase 2 Deliverables

- [ ] GitOps working with real repositories
- [ ] IndexService with sqlite-vec integration
- [ ] EmbeddingService with lazy loading

### Phase 2 Exit Criteria

- [ ] Can create notes in git
- [ ] Can query vectors in SQLite
- [ ] Can generate embeddings
- [ ] All Phase 2 tests pass

---

## Phase 3: Core Services

**Goal**: Implement capture and recall orchestration

### Task 3.1: Implement CaptureService

- **Description**: Main capture orchestration with concurrency safety
- **Files to Create**: `src/git_notes_memory/capture.py`
- **Methods to Implement**:
  - [ ] `capture(namespace, summary, content, ...)` - Generic capture
  - [ ] `capture_decision(spec, summary, ...)` - ADR format
  - [ ] `capture_blocker(spec, summary, ...)` - Blocker format
  - [ ] `resolve_blocker(memory_id, resolution, ...)` - Resolution
  - [ ] `capture_learning(summary, insight, ...)` - Learning format
  - [ ] `capture_progress(spec, summary, ...)` - Progress format
  - [ ] `capture_retrospective(spec, summary, ...)` - Retro format
  - [ ] `capture_pattern(summary, type, ...)` - Pattern format
  - [ ] `capture_review(spec, summary, ...)` - Review format
  - [ ] `_acquire_lock()` / `_release_lock()` - Concurrency
- **Flow**:
  1. Validate input
  2. Acquire lock
  3. Create YAML front matter
  4. Append to git note
  5. Generate embedding (graceful degradation)
  6. Insert into index
  7. Release lock
  8. Return CaptureResult
- **Acceptance Criteria**:
  - [ ] All capture methods work
  - [ ] Lock prevents concurrent corruption
  - [ ] Embedding failure doesn't block capture
  - [ ] Integration tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/capture.py`

### Task 3.2: Implement RecallService

- **Description**: Memory retrieval and hydration
- **Files to Create**: `src/git_notes_memory/recall.py`
- **Methods to Implement**:
  - [ ] `search(query, namespace, spec, ...)` - Semantic search
  - [ ] `hydrate(memory, level)` - Progressive loading
  - [ ] `context(spec)` - All memories for spec
  - [ ] `recent(limit, namespace)` - Recent memories
  - [ ] `similar(memory_id, limit)` - Find similar
  - [ ] `by_commit(sha)` - By commit
- **Hydration Levels**:
  - SUMMARY: Return as-is from index
  - FULL: Load full content from git notes
  - FILES: Load file snapshots from commit
- **Acceptance Criteria**:
  - [ ] Search returns relevant results
  - [ ] Hydration levels work correctly
  - [ ] Context groups by namespace
  - [ ] Integration tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/recall.py`

### Task 3.3: Implement SyncService

- **Description**: Index synchronization with git notes
- **Files to Create**: `src/git_notes_memory/sync.py`
- **Methods to Implement**:
  - [ ] `sync_note_to_index(commit, namespace)` - Sync single note
  - [ ] `reindex(full)` - Rebuild index
  - [ ] `verify_consistency()` - Check index vs notes
  - [ ] `collect_notes()` - Gather all notes
- **Acceptance Criteria**:
  - [ ] Full reindex works
  - [ ] Incremental sync works
  - [ ] Consistency verification detects drift
  - [ ] Integration tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/sync.py`

### Task 3.4: Create Package Entry Point

- **Description**: Lazy-loading factory functions in __init__.py
- **Files to Create**: `src/git_notes_memory/__init__.py`
- **Exports**:
  - [ ] `get_capture_service()` - Factory for CaptureService
  - [ ] `get_recall_service()` - Factory for RecallService
  - [ ] `get_sync_service()` - Factory for SyncService
  - [ ] `is_auto_capture_enabled()` - Check env var
  - [ ] All model classes
  - [ ] All exception classes
- **Acceptance Criteria**:
  - [ ] Lazy loading prevents import-time model load
  - [ ] Clean public API
  - [ ] Version exposed via `__version__`

**Source Reference**: `~/Projects/zircote/claude-spec/memory/__init__.py`

### Phase 3 Deliverables

- [ ] CaptureService with all capture methods
- [ ] RecallService with search and hydration
- [ ] SyncService for index management
- [ ] Clean public API

### Phase 3 Exit Criteria

- [ ] Can capture and recall memories end-to-end
- [ ] Concurrent captures don't corrupt
- [ ] Reindex rebuilds correctly
- [ ] All Phase 3 tests pass

---

## Phase 4: Advanced Features

**Goal**: Implement search optimization, pattern detection, lifecycle management

### Task 4.1: Implement SearchOptimizer

- **Description**: Query expansion and result re-ranking
- **Files to Create**: `src/git_notes_memory/search.py`
- **Components**:
  - [ ] `QueryExpander` - Synonym expansion
  - [ ] `ResultReranker` - Recency, namespace, tag boosting
  - [ ] `SearchCache` - LRU cache with TTL
- **Methods**:
  - [ ] `expand_query(query)` - Add synonyms
  - [ ] `rerank(results, query, filters)` - Boost scores
  - [ ] `cache_get(hash)` / `cache_set(hash, results)` - Caching
- **Acceptance Criteria**:
  - [ ] Query expansion improves recall
  - [ ] Re-ranking improves relevance
  - [ ] Cache reduces redundant searches
  - [ ] Unit tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/search.py`

### Task 4.2: Implement PatternManager

- **Description**: Pattern detection across memories
- **Files to Create**: `src/git_notes_memory/patterns.py`
- **Methods**:
  - [ ] `detect_patterns(memories)` - Find patterns
  - [ ] `promote(pattern_id)` - Validate pattern
  - [ ] `demote(pattern_id)` - Invalidate pattern
  - [ ] `get_patterns(status)` - List by status
- **Pattern Types**:
  - SUCCESS_PATTERN
  - ANTI_PATTERN
  - WORKFLOW_PATTERN
  - DECISION_PATTERN
- **Acceptance Criteria**:
  - [ ] Detects common patterns
  - [ ] Confidence scoring works
  - [ ] Lifecycle transitions work
  - [ ] Unit tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/patterns.py`

### Task 4.3: Implement LifecycleManager

- **Description**: Memory aging and archival
- **Files to Create**: `src/git_notes_memory/lifecycle.py`
- **Methods**:
  - [ ] `calculate_decay(timestamp)` - Decay score
  - [ ] `age_memories()` - Transition states
  - [ ] `archive_old_memories(days)` - Archive old
  - [ ] `get_state(memory)` - Current state
- **States**: ACTIVE → AGING → STALE → ARCHIVED → TOMBSTONE
- **Acceptance Criteria**:
  - [ ] Decay formula correct
  - [ ] State transitions work
  - [ ] Archive compresses content
  - [ ] Unit tests

**Source Reference**: `~/Projects/zircote/claude-spec/memory/lifecycle.py`

### Phase 4 Deliverables

- [ ] SearchOptimizer with query expansion and re-ranking
- [ ] PatternManager for pattern detection
- [ ] LifecycleManager for aging

### Phase 4 Exit Criteria

- [ ] Search quality improved
- [ ] Patterns detected correctly
- [ ] Lifecycle transitions work
- [ ] All Phase 4 tests pass

---

## Phase 5: Plugin Integration

**Goal**: Create Claude Code plugin wrapper

### Task 5.1: Create Plugin Structure

- **Description**: Initialize Claude Code plugin skeleton
- **Files to Create**:
  - [ ] `.claude-plugin/plugin.json` - Manifest
  - [ ] `README.md` - Plugin documentation
- **Acceptance Criteria**:
  - [ ] Valid plugin.json structure
  - [ ] Plugin loads in Claude Code

### Task 5.2: Implement Commands

- **Description**: Create slash commands for memory operations
- **Files to Create**:
  - [ ] `commands/remember.md` - /remember command
  - [ ] `commands/recall.md` - /recall command
  - [ ] `commands/context.md` - /context command
  - [ ] `commands/memory.md` - /memory admin commands
- **Commands**:
  - [ ] `/remember <namespace> <summary>` - Capture with body prompt
  - [ ] `/recall <query>` - Search with filters
  - [ ] `/context <spec>` - Load all spec memories
  - [ ] `/memory status` - Show stats
  - [ ] `/memory reindex [--full]` - Rebuild index
  - [ ] `/memory verify` - Check consistency
  - [ ] `/memory gc [--dry-run]` - Garbage collect
- **Acceptance Criteria**:
  - [ ] Commands invoke library correctly
  - [ ] Output is well-formatted
  - [ ] Error handling is user-friendly

### Task 5.3: Implement Skills

- **Description**: Create skill for automatic memory use
- **Files to Create**:
  - [ ] `skills/memory-retrieval/SKILL.md` - Memory retrieval skill
- **Skill Capabilities**:
  - [ ] Recall relevant memories for current task
  - [ ] Capture important decisions automatically
  - [ ] Provide context from past sessions
- **Acceptance Criteria**:
  - [ ] Skill triggers appropriately
  - [ ] Provides useful context
  - [ ] Doesn't over-capture

### Task 5.4: Implement Hooks (Optional)

- **Description**: Create optional prompt capture hook
- **Files to Create**:
  - [ ] `hooks/hooks.json` - Hook configuration
  - [ ] `hooks/prompt_capture.py` - Hook implementation
- **Behavior**:
  - [ ] Disabled by default
  - [ ] Enabled via `.prompt-log-enabled` marker
  - [ ] Captures to `elicitation` namespace
  - [ ] Filters sensitive content
- **Acceptance Criteria**:
  - [ ] Hook only active when marker present
  - [ ] Captures useful prompts
  - [ ] Doesn't capture sensitive data

**Source Reference**: `~/Projects/zircote/claude-spec/hooks/prompt_capture.py`

### Phase 5 Deliverables

- [ ] Working Claude Code plugin
- [ ] All commands functional
- [ ] Memory retrieval skill
- [ ] Optional prompt capture hook

### Phase 5 Exit Criteria

- [ ] Plugin installs in Claude Code
- [ ] All commands work
- [ ] Skill provides value
- [ ] Hook captures correctly (when enabled)

---

## Phase 6: Polish & Release

**Goal**: Testing, documentation, and distribution

### Task 6.1: Comprehensive Testing

- **Description**: Achieve ≥90% test coverage
- **Test Files**:
  - [ ] Unit tests for all modules
  - [ ] Integration tests for end-to-end flows
  - [ ] Performance benchmarks
- **Acceptance Criteria**:
  - [ ] ≥90% coverage
  - [ ] All edge cases covered
  - [ ] CI passes

### Task 6.2: Documentation

- **Description**: Complete documentation
- **Files to Create**:
  - [ ] `README.md` - Full project documentation
  - [ ] `docs/USER_GUIDE.md` - User-facing guide
  - [ ] `docs/DEVELOPER_GUIDE.md` - API reference
  - [ ] `CHANGELOG.md` - Version history
- **Acceptance Criteria**:
  - [ ] Installation instructions clear
  - [ ] All commands documented
  - [ ] API reference complete
  - [ ] Examples provided

### Task 6.3: PyPI Release

- **Description**: Publish to PyPI
- **Steps**:
  - [ ] Finalize `pyproject.toml`
  - [ ] Build with `python -m build`
  - [ ] Upload with `twine upload dist/*`
  - [ ] Verify installation: `pip install git-notes-memory`
- **Acceptance Criteria**:
  - [ ] Package installs from PyPI
  - [ ] Version number correct
  - [ ] Dependencies resolve

### Task 6.4: GitHub Release

- **Description**: Create GitHub release
- **Steps**:
  - [ ] Tag version: `git tag v1.0.0`
  - [ ] Push tag: `git push origin v1.0.0`
  - [ ] Create release notes
  - [ ] Attach source archive
- **Acceptance Criteria**:
  - [ ] Release published
  - [ ] Release notes complete
  - [ ] Can install via GitHub URL

### Phase 6 Deliverables

- [ ] Comprehensive test suite
- [ ] Complete documentation
- [ ] PyPI package
- [ ] GitHub release

### Phase 6 Exit Criteria

- [ ] ≥90% test coverage
- [ ] Documentation complete
- [ ] Package on PyPI
- [ ] Release on GitHub
- [ ] README badges green

---

## Dependency Graph

```
Phase 1 (Foundation)
  ├── 1.1 Package Structure
  ├── 1.2 Models ─────────────┐
  ├── 1.3 Config ─────────────┤
  ├── 1.4 Exceptions ─────────┤
  ├── 1.5 Utils ──────────────┤
  └── 1.6 Note Parser ────────┘
                              │
                              ▼
Phase 2 (Storage Layer)
  ├── 2.1 GitOps ◄────────────┤
  ├── 2.2 IndexService ◄──────┤
  └── 2.3 EmbeddingService ◄──┘
                              │
                              ▼
Phase 3 (Core Services)
  ├── 3.1 CaptureService ◄────┤
  ├── 3.2 RecallService ◄─────┤
  ├── 3.3 SyncService ◄───────┤
  └── 3.4 Package Entry Point ┘
                              │
                              ▼
Phase 4 (Advanced Features)
  ├── 4.1 SearchOptimizer
  ├── 4.2 PatternManager
  └── 4.3 LifecycleManager
                              │
                              ▼
Phase 5 (Plugin Integration)
  ├── 5.1 Plugin Structure
  ├── 5.2 Commands
  ├── 5.3 Skills
  └── 5.4 Hooks (Optional)
                              │
                              ▼
Phase 6 (Polish & Release)
  ├── 6.1 Testing
  ├── 6.2 Documentation
  ├── 6.3 PyPI Release
  └── 6.4 GitHub Release
```

---

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| sqlite-vec unavailable | Test early, document fallback | Phase 2 |
| Embedding model download fails | Implement retry, clear error messages | Phase 2 |
| Git notes conflict | Test namespace configuration thoroughly | Phase 2 |
| Concurrent corruption | Extensive lock testing | Phase 3 |
| Breaking sentence-transformers changes | Pin version, CI matrix | Phase 6 |

---

## Testing Checklist

- [ ] Unit tests for all modules (Phase 1-4)
- [ ] Integration tests for capture/recall (Phase 3)
- [ ] Integration tests for git operations (Phase 2)
- [ ] Performance benchmarks (Phase 6)
- [ ] CLI command tests (Phase 5)
- [ ] Plugin installation tests (Phase 5)
- [ ] Coverage ≥90%

---

## Documentation Tasks

- [ ] README.md with installation and quick start
- [ ] USER_GUIDE.md with commands and examples
- [ ] DEVELOPER_GUIDE.md with API reference
- [ ] Inline docstrings on all public APIs
- [ ] CHANGELOG.md with version history

---

## Launch Checklist

- [ ] All tests passing
- [ ] Documentation complete
- [ ] mypy --strict passes
- [ ] ruff check passes
- [ ] Package builds successfully
- [ ] PyPI upload successful
- [ ] GitHub release created
- [ ] Plugin installs in Claude Code
- [ ] Commands work end-to-end
- [ ] README badges show passing
