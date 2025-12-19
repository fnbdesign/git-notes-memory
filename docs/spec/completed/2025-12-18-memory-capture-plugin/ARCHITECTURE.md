---
document_type: architecture
project_id: SPEC-2025-12-18-001
version: 1.0.0
last_updated: 2025-12-18T00:00:00Z
status: draft
---

# Memory Capture Plugin - Technical Architecture

## System Overview

The Memory Capture Plugin is a hybrid Python library + Claude Code plugin that provides Git-native, semantically-searchable context storage. The system uses git notes as the source of truth with a local SQLite + sqlite-vec index for fast retrieval.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Claude Code Plugin Layer                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Commands   │  │   Skills    │  │   Agents    │  │       Hooks         │ │
│  │ /remember   │  │ memory-     │  │  memory-    │  │  prompt_capture.py  │ │
│  │ /recall     │  │ retrieval/  │  │  assistant  │  │  (optional)         │ │
│  │ /context    │  │ SKILL.md    │  │             │  │                     │ │
│  │ /memory     │  │             │  │             │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │            │
└─────────┼────────────────┼────────────────┼─────────────────────┼────────────┘
          │                │                │                     │
          ▼                ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Python Library Core (git-notes-memory)               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────────────┐ │
│  │ CaptureService │    │  RecallService │    │     SearchOptimizer        │ │
│  │                │    │                │    │                            │ │
│  │ - capture()    │    │ - search()     │    │ - QueryExpander            │ │
│  │ - capture_*()  │    │ - hydrate()    │    │ - ResultReranker           │ │
│  │                │    │ - context()    │    │ - SearchCache              │ │
│  └───────┬────────┘    └───────┬────────┘    └─────────────┬──────────────┘ │
│          │                     │                           │                │
│          ▼                     ▼                           ▼                │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         IndexService (SQLite + sqlite-vec)             │ │
│  │                                                                        │ │
│  │  - initialize()    - insert()      - search_vector()    - get_stats() │ │
│  │  - get()           - update()      - delete()           - verify()    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│          │                                                                  │
│          ▼                                                                  │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────────────┐ │
│  │ EmbeddingService│    │    GitOps      │    │      SyncService          │ │
│  │                │    │                │    │                            │ │
│  │ - embed()      │    │ - add_note()   │    │ - sync_note_to_index()    │ │
│  │ - embed_batch()│    │ - show_note()  │    │ - reindex()               │ │
│  │ - unload()     │    │ - list_notes() │    │ - verify_consistency()    │ │
│  └────────────────┘    └────────────────┘    └────────────────────────────┘ │
│                                                                             │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────────────┐ │
│  │PatternManager  │    │LifecycleManager│    │       Config               │ │
│  │                │    │                │    │                            │ │
│  │ - detect()     │    │ - age_memories()│   │ - namespaces               │ │
│  │ - promote()    │    │ - archive()    │    │ - storage paths            │ │
│  │ - demote()     │    │ - decay_score()│    │ - embedding model          │ │
│  └────────────────┘    └────────────────┘    └────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │                          │                          │
          ▼                          ▼                          ▼
┌─────────────────┐      ┌────────────────────┐      ┌────────────────────────┐
│   Git Notes     │      │  SQLite + vec0     │      │   Models Cache         │
│                 │      │                    │      │                        │
│ refs/notes/mem/*│      │ ~/.local/share/    │      │ ~/.local/share/        │
│ (per repo)      │      │ memory-plugin/     │      │ memory-plugin/models/  │
│                 │      │ index.db           │      │ all-MiniLM-L6-v2/      │
└─────────────────┘      └────────────────────┘      └────────────────────────┘
```

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Source of truth | Git notes | Distributed, versioned, syncs with code |
| Search index | SQLite + sqlite-vec | Fast KNN, single file, no server |
| Embeddings | sentence-transformers | Local, no API keys, fast |
| Plugin structure | Hybrid lib + plugin | Reusable core, flexible integration |
| Storage location | XDG compliant | Standard, cross-platform |
| Git namespace | Configurable | Avoid conflicts, flexibility |

## Component Design

### Component 1: CaptureService

- **Purpose**: Orchestrates memory capture operations
- **Responsibilities**:
  - Validate input (namespace, content length)
  - Acquire file lock for concurrency
  - Create YAML front matter metadata
  - Write to git notes (append for concurrency safety)
  - Generate embedding (graceful degradation)
  - Insert into index
  - Release lock
- **Interfaces**:
  - `capture(namespace, summary, content, spec, tags, phase)` → `CaptureResult`
  - `capture_decision(spec, summary, context, rationale, alternatives, tags)` → `CaptureResult`
  - `capture_blocker(spec, summary, description, impact, tags)` → `CaptureResult`
  - `resolve_blocker(memory_id, resolution, tags)` → `CaptureResult`
  - `capture_learning(summary, insight, context, tags)` → `CaptureResult`
  - `capture_progress(spec, summary, milestone, tags)` → `CaptureResult`
  - `capture_retrospective(spec, summary, content, outcome, tags)` → `CaptureResult`
  - `capture_pattern(summary, type, evidence, confidence, tags)` → `CaptureResult`
  - `capture_review(spec, summary, findings, tags)` → `CaptureResult`
- **Dependencies**: IndexService, EmbeddingService, GitOps, Config
- **Technology**: Python, fcntl for file locking

### Component 2: RecallService

- **Purpose**: Retrieves memories via semantic search and filters
- **Responsibilities**:
  - Execute vector similarity search
  - Apply namespace, spec, time filters
  - Progressive hydration (SUMMARY → FULL → FILES)
  - Batch retrieval for N+1 prevention
- **Interfaces**:
  - `search(query, namespace, spec, limit, time_range)` → `List[MemoryResult]`
  - `hydrate(memory, level)` → `HydratedMemory`
  - `context(spec)` → `SpecContext`
  - `recent(limit, namespace)` → `List[Memory]`
  - `similar(memory_id, limit)` → `List[MemoryResult]`
  - `by_commit(sha)` → `List[Memory]`
- **Dependencies**: IndexService, EmbeddingService, SearchOptimizer, GitOps
- **Technology**: Python

### Component 3: IndexService

- **Purpose**: Manages SQLite + sqlite-vec storage
- **Responsibilities**:
  - Schema creation and migration
  - CRUD operations for memories
  - Vector similarity search (KNN)
  - Statistics and health checks
- **Interfaces**:
  - `initialize()` → None
  - `insert(memory, embedding)` → None
  - `get(memory_id)` → `Optional[Memory]`
  - `get_batch(memory_ids)` → `List[Memory]`
  - `get_by_spec(spec)` → `List[Memory]`
  - `search_vector(embedding, limit, filters)` → `List[MemoryResult]`
  - `update(memory_id, updates)` → None
  - `delete(memory_id)` → None
  - `list_recent(limit, namespace)` → `List[Memory]`
  - `get_stats()` → `IndexStats`
  - `verify()` → `VerificationResult`
- **Dependencies**: Config (for paths)
- **Technology**: SQLite, sqlite-vec extension

### Component 4: EmbeddingService

- **Purpose**: Generates vector embeddings for text
- **Responsibilities**:
  - Lazy model loading
  - Single and batch embedding generation
  - Model caching to XDG directory
  - Graceful error handling
- **Interfaces**:
  - `embed(text)` → `np.ndarray` (384D vector)
  - `embed_batch(texts)` → `np.ndarray` (Nx384)
  - `get_dimensions()` → `int`
  - `is_loaded()` → `bool`
  - `unload()` → None
- **Dependencies**: Config (for model path)
- **Technology**: sentence-transformers, configurable model

### Component 5: GitOps

- **Purpose**: Wraps git command execution
- **Responsibilities**:
  - Git notes CRUD operations
  - Commit and file inspection
  - Security validation (refs, paths)
  - Auto-configuration of remote sync
- **Interfaces**:
  - `add_note(commit, content, namespace)` → None
  - `append_note(commit, content, namespace)` → None
  - `show_note(commit, namespace)` → `str`
  - `list_notes(namespace)` → `List[Tuple[sha, commit]]`
  - `remove_note(commit, namespace)` → None
  - `get_commit_sha(ref)` → `str`
  - `get_commit_info(sha)` → `CommitInfo`
  - `get_file_at_commit(sha, path)` → `str`
  - `get_changed_files(sha)` → `List[str]`
  - `configure_sync(namespace)` → None
- **Dependencies**: Config (for namespace)
- **Technology**: subprocess, git CLI

### Component 6: SyncService

- **Purpose**: Synchronizes index with git notes
- **Responsibilities**:
  - Parse notes and sync to index
  - Full reindex from all notes
  - Consistency verification
- **Interfaces**:
  - `sync_note_to_index(commit, namespace)` → None
  - `reindex(full=False)` → `int` (count of indexed)
  - `verify_consistency()` → `VerificationResult`
  - `collect_notes()` → `List[NoteRecord]`
- **Dependencies**: IndexService, GitOps, EmbeddingService, NoteParser
- **Technology**: Python

### Component 7: SearchOptimizer

- **Purpose**: Enhances search quality
- **Responsibilities**:
  - Query expansion with synonyms
  - Result re-ranking (recency, namespace priority)
  - Search result caching
- **Interfaces**:
  - `expand_query(query)` → `str` (expanded query)
  - `rerank(results, query, filters)` → `List[MemoryResult]`
  - `cache_get(query_hash)` → `Optional[List[MemoryResult]]`
  - `cache_set(query_hash, results)` → None
- **Dependencies**: Config (for weights)
- **Technology**: Python, OrderedDict for LRU cache

### Component 8: PatternManager

- **Purpose**: Detects and manages patterns across memories
- **Responsibilities**:
  - Pattern detection (success, anti-pattern, workflow, decision)
  - Lifecycle management (candidate → validated → promoted)
  - Confidence scoring
- **Interfaces**:
  - `detect_patterns(memories)` → `List[Pattern]`
  - `promote(pattern_id)` → None
  - `demote(pattern_id)` → None
  - `get_patterns(status)` → `List[Pattern]`
- **Dependencies**: IndexService, RecallService
- **Technology**: Python, keyword-based classification

### Component 9: LifecycleManager

- **Purpose**: Manages memory aging and archival
- **Responsibilities**:
  - Calculate decay scores
  - Transition memory states
  - Archive old memories
- **Interfaces**:
  - `calculate_decay(timestamp)` → `float`
  - `age_memories()` → `int` (count aged)
  - `archive_old_memories(age_days)` → `int`
  - `get_state(memory)` → `LifecycleState`
- **Dependencies**: IndexService, Config
- **Technology**: Python, exponential decay formula

## Data Design

### Data Models

```python
@dataclass(frozen=True)
class Memory:
    id: str                    # UUID
    commit_sha: str            # Git commit this memory is attached to
    namespace: str             # One of 10 types
    summary: str               # ≤100 char summary
    content: str               # Full markdown content
    timestamp: datetime        # When captured
    spec: Optional[str]        # Project/spec slug
    phase: Optional[str]       # Lifecycle phase
    tags: List[str]            # Categorization tags
    status: str                # active, resolved, archived, tombstone
    relates_to: List[str]      # Related memory IDs

@dataclass(frozen=True)
class MemoryResult:
    memory: Memory
    distance: float            # Similarity distance (lower = more similar)

@dataclass(frozen=True)
class HydratedMemory:
    memory: Memory
    full_content: str          # Complete note from git
    files: Dict[str, str]      # File snapshots from commit

class HydrationLevel(Enum):
    SUMMARY = 1                # Just metadata
    FULL = 2                   # + full note content
    FILES = 3                  # + file snapshots

@dataclass(frozen=True)
class SpecContext:
    spec: str
    memories: List[Memory]
    by_namespace: Dict[str, List[Memory]]

@dataclass(frozen=True)
class IndexStats:
    total_memories: int
    by_namespace: Dict[str, int]
    by_spec: Dict[str, int]
    index_size_bytes: int
    last_capture: Optional[datetime]

@dataclass(frozen=True)
class CaptureResult:
    success: bool
    memory_id: Optional[str]
    indexed: bool
    error: Optional[str]

@dataclass
class CaptureAccumulator:
    results: List[CaptureResult]

    def add(self, result: CaptureResult) -> None: ...
    def summary(self) -> str: ...
```

### Database Schema

```sql
-- Main metadata table
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    commit_sha TEXT NOT NULL,
    namespace TEXT NOT NULL,
    spec TEXT,
    phase TEXT,
    summary TEXT NOT NULL,
    full_content TEXT,
    tags JSON DEFAULT '[]',
    timestamp DATETIME NOT NULL,
    status TEXT DEFAULT 'active',
    relates_to JSON DEFAULT '[]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_memories_spec ON memories(spec);
CREATE INDEX idx_memories_namespace ON memories(namespace);
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX idx_memories_commit ON memories(commit_sha);
CREATE INDEX idx_memories_status ON memories(status);

-- Vector table for semantic search (sqlite-vec)
CREATE VIRTUAL TABLE vec_memories USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[384]
);
```

### YAML Front Matter Format

```yaml
---
type: decisions                   # Required: namespace
spec: user-auth                   # Required: spec/project slug (or null)
timestamp: 2025-12-18T10:30:00Z   # Required: ISO 8601
summary: Chose JWT over sessions  # Required: ≤100 chars
tags: [authentication, security]  # Optional: categorization
phase: architecture               # Optional: lifecycle phase
status: active                    # Optional: active/resolved/archived
relates_to:                       # Optional: linked memories
  - decisions:abc123:1
---

## Full markdown body here

The decision content with full context, rationale, and details.
```

### Data Flow

```
┌─────────────┐
│   User      │
│  /remember  │
└──────┬──────┘
       │
       ▼
┌──────────────┐    ┌────────────────┐
│ CaptureService│───▶│ Validate Input │
└──────┬───────┘    └────────────────┘
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
┌────────────────┐                   ┌────────────────┐
│ EmbeddingService│                   │    GitOps      │
│ embed(text)    │                   │ append_note()  │
└───────┬────────┘                   └───────┬────────┘
        │                                    │
        │                                    │
        ▼                                    ▼
┌────────────────────────────────────────────────────┐
│                   IndexService                      │
│              insert(memory, embedding)             │
└────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│ CaptureResult │
│ success: true │
│ indexed: true │
└──────────────┘
```

### Storage Paths

```
~/.local/share/memory-plugin/
├── index.db                    # SQLite database + sqlite-vec
├── models/
│   └── all-MiniLM-L6-v2/       # Sentence transformer model cache
└── config.toml                 # User configuration (optional)

Repository:
├── refs/notes/mem/             # Git notes namespace (configurable)
│   ├── decisions               # Decision memories
│   ├── learnings               # Learning memories
│   └── ...                     # Other namespaces
```

## API Design

### Python Library API

```python
from git_notes_memory import (
    get_capture_service,
    get_recall_service,
    Memory,
    MemoryResult,
    HydrationLevel,
)

# Capture
capture = get_capture_service()
result = capture.capture(
    namespace="decisions",
    summary="Chose FastAPI over Flask",
    content="Full explanation...",
    spec="api-redesign",
    tags=["framework", "performance"],
)

# Recall
recall = get_recall_service()
results = recall.search(
    query="API framework decision",
    namespace="decisions",
    limit=5,
)

# Hydrate
for r in results:
    hydrated = recall.hydrate(r.memory, HydrationLevel.FULL)
    print(hydrated.full_content)

# Context
context = recall.context("api-redesign")
for ns, memories in context.by_namespace.items():
    print(f"{ns}: {len(memories)} memories")
```

### Command Interface

| Command | Purpose | Example |
|---------|---------|---------|
| `/remember <namespace> <summary>` | Capture memory | `/remember decision Chose PostgreSQL over MySQL` |
| `/recall <query>` | Search memories | `/recall database selection` |
| `/context <spec>` | Load all memories for spec | `/context api-redesign` |
| `/memory status` | Show index stats | `/memory status` |
| `/memory reindex` | Rebuild index | `/memory reindex --full` |
| `/memory verify` | Check consistency | `/memory verify` |
| `/memory gc` | Garbage collect | `/memory gc --dry-run` |

## Integration Points

### Claude Code Plugin Integration

```
memory-plugin/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── commands/
│   ├── remember.md              # /remember command
│   ├── recall.md                # /recall command
│   ├── context.md               # /context command
│   └── memory.md                # /memory admin commands
├── skills/
│   └── memory-retrieval/
│       └── SKILL.md             # Skill for automatic memory use
├── agents/
│   └── memory-assistant.md      # Memory-aware agent
├── hooks/
│   └── hooks.json               # Optional prompt capture
└── .mcp.json                    # Optional MCP server config
```

### Plugin Manifest (plugin.json)

```json
{
  "name": "memory-plugin",
  "version": "1.0.0",
  "description": "Git-native, semantically-searchable memory for Claude Code",
  "author": {
    "name": "Your Name",
    "url": "https://github.com/yourname"
  },
  "repository": "https://github.com/yourname/memory-plugin",
  "license": "MIT",
  "keywords": ["memory", "git-notes", "semantic-search", "context"]
}
```

## Security Design

### Concurrency Control

```python
# File locking for concurrent capture
import fcntl

def acquire_capture_lock():
    lock_path = config.lock_file_path  # ~/.local/share/memory-plugin/.capture.lock
    fd = open(lock_path, 'w')
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd

def release_capture_lock(fd):
    fcntl.flock(fd, fcntl.LOCK_UN)
    fd.close()
```

### Input Validation

```python
def validate_git_ref(ref: str) -> bool:
    """Prevent command injection via malicious refs."""
    pattern = r'^[a-zA-Z0-9_\-./]+$'
    return bool(re.match(pattern, ref)) and '..' not in ref

def validate_path(path: str) -> bool:
    """Prevent path traversal attacks."""
    return '\0' not in path and not os.path.isabs(path)

def validate_content_length(content: str, max_bytes: int = 102400) -> bool:
    """Prevent oversized content (100KB default)."""
    return len(content.encode('utf-8')) <= max_bytes
```

### Security Considerations

| Threat | Mitigation |
|--------|------------|
| Command injection via git ref | Regex validation, no shell=True |
| Path traversal | No absolute paths, no null bytes |
| Concurrent corruption | File locking (fcntl.flock) |
| Resource exhaustion | Content limits, query timeouts |
| Sensitive data in memory | User responsibility, documentation |

## Performance Considerations

### Expected Load

- Captures per day: 10-50
- Searches per session: 50-200
- Total memories per repo: 1,000-10,000
- Concurrent sessions: 1-3

### Performance Targets

| Operation | Target | Technique |
|-----------|--------|-----------|
| Capture | ≤500ms | Async embedding optional |
| Search | ≤200ms | sqlite-vec KNN, indexes |
| Hydrate (SUMMARY) | ≤10ms | Already in memory |
| Hydrate (FULL) | ≤50ms | Single git notes show |
| Hydrate (FILES) | ≤100ms | Parallel file reads, limits |

### Optimization Strategies

1. **Lazy loading**: Embedding model loads on first use
2. **Batch retrieval**: `get_batch()` prevents N+1 queries
3. **Search cache**: LRU cache with 5-min TTL, 100 entries
4. **File limits**: Max 20 files, 100KB each for hydration
5. **Index optimization**: Proper indexes on frequently queried columns
6. **Append-only writes**: `append_note()` for concurrent safety

## Testing Strategy

### Unit Testing

- All services have dedicated test files
- Mock git operations for isolation
- Mock embedding service for speed
- Target: ≥90% coverage

### Integration Testing

- Real git repository operations
- SQLite database operations
- End-to-end capture/recall flows

### Performance Testing

- Benchmark capture latency
- Benchmark search at 1K, 5K, 10K memories
- Memory usage profiling

## Deployment Considerations

### Python Package

```toml
# pyproject.toml
[project]
name = "git-notes-memory"
version = "1.0.0"
description = "Git-native, semantically-searchable memory"
requires-python = ">=3.11"
dependencies = [
    "pyyaml>=6.0",
    "sentence-transformers>=2.2.0",
    "sqlite-vec>=0.1.1",
]

[project.scripts]
memory = "git_notes_memory.cli:main"
```

### Claude Code Plugin

```bash
# Installation
/plugin install yourname/memory-plugin

# Or local development
/plugin marketplace add ./dev-marketplace
/plugin install memory-plugin@dev-marketplace
```

### Configuration

```toml
# ~/.local/share/memory-plugin/config.toml
[storage]
index_path = "~/.local/share/memory-plugin/index.db"
models_path = "~/.local/share/memory-plugin/models"

[git]
namespace = "refs/notes/mem"  # Configurable

[embedding]
model = "all-MiniLM-L6-v2"
dimensions = 384

[search]
cache_ttl_seconds = 300
cache_max_entries = 100
default_limit = 10

[lifecycle]
decay_half_life_days = 30
archive_after_days = 90
```

## Future Considerations

1. **Migration tool**: Import memories from claude-spec
2. **Cross-repo search**: Query memories from multiple repositories
3. **LLM summarization**: Auto-summarize old memories for compression
4. **Web UI**: Local server for browsing memories
5. **Team namespaces**: Per-user vs shared memory spaces
6. **Alternative embeddings**: API-based (OpenAI, Cohere) for better quality
