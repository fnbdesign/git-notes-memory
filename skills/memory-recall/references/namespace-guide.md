# Namespace Guide

Detailed guidance on when and how to use each memory namespace.

## Namespace Overview

The memory system organizes memories into five namespaces, each serving a distinct purpose:

| Namespace | Purpose | Persistence | Search Priority |
|-----------|---------|-------------|-----------------|
| `decisions` | Architectural choices | Long-term | High |
| `learnings` | Knowledge discoveries | Long-term | Medium |
| `context` | Project information | Medium-term | Medium |
| `preferences` | User preferences | Long-term | Low |
| `patterns` | Recurring solutions | Long-term | High |

## Decisions Namespace

### When to Store

- Architectural choices ("We chose PostgreSQL over MySQL")
- Technology selections ("Using FastAPI for the API layer")
- Design decisions ("Events will be stored in append-only log")
- Trade-off resolutions ("Prioritized consistency over availability")

### When to Recall

- Questions starting with "why did we..."
- When similar decisions need to be made
- During code reviews questioning design
- When onboarding new team members

### Example Memories

```
Decision: Use PostgreSQL for main database
Rationale: JSONB support, strong Python ecosystem, team familiarity
Trade-offs: Slightly more complex than SQLite, but scales better
Date: 2024-01-15
```

### Search Queries

- "database choice", "why postgres"
- "api framework decision"
- "architecture decision authentication"

## Learnings Namespace

### When to Store

- TIL discoveries ("pytest fixtures can be module-scoped")
- Bug root causes ("Memory leak caused by unclosed connections")
- Performance insights ("Batch inserts 10x faster than individual")
- Gotchas and edge cases ("SQLite doesn't enforce foreign keys by default")

### When to Recall

- Encountering similar problems
- Working with related technologies
- Debugging issues
- Code review discussions

### Example Memories

```
Learning: pytest fixtures with scope="module" persist across tests
Context: Discovered while optimizing slow test suite
Application: Use for expensive setup like database connections
Date: 2024-01-12
```

### Search Queries

- "pytest slow tests"
- "database performance"
- "memory leak python"

## Context Namespace

### When to Store

- Project structure ("Tests are in tests/, fixtures in tests/fixtures/")
- Conventions ("We use snake_case for Python, camelCase for JS")
- Configuration notes ("Dev server runs on port 8000")
- File locations ("Database migrations in migrations/versions/")

### When to Recall

- Starting work on unfamiliar area
- Looking for specific files
- Understanding project conventions
- Onboarding questions

### Example Memories

```
Context: Database schema defined in models/
Files: models/user.py, models/order.py, models/product.py
Migration: Use `alembic revision --autogenerate` for schema changes
Date: 2024-01-10
```

### Search Queries

- "where are tests"
- "database migration"
- "project structure"

## Preferences Namespace

### When to Store

- Code style preferences ("Prefer composition over inheritance")
- Tool preferences ("Use ruff instead of black+isort")
- Communication style ("Concise responses preferred")
- Workflow preferences ("Always run tests before committing")

### When to Recall

- Generating code that should match user style
- Suggesting tools or approaches
- Formatting output
- Making recommendations

### Example Memories

```
Preference: Prefer functional style over classes for utilities
Reason: Easier to test, compose, and understand
Example: Use pure functions with explicit inputs/outputs
Date: 2024-01-08
```

### Search Queries

- "coding style"
- "preferred tools"
- "how does user like"

## Patterns Namespace

### When to Store

- Recurring solutions ("Error handling follows Result pattern")
- Common code structures ("API endpoints follow controller pattern")
- Reusable approaches ("Retry with exponential backoff for network calls")
- Idioms ("Use context managers for resource cleanup")

### When to Recall

- Implementing similar functionality
- Code review for consistency
- Suggesting implementations
- Teaching patterns to new code areas

### Example Memories

```
Pattern: Error handling with Result type
Usage: All service methods return Result[T, Error] instead of raising
Implementation: See utils/result.py for Result class
Applies to: Service layer, not controllers
Date: 2024-01-05
```

### Search Queries

- "error handling pattern"
- "api endpoint structure"
- "retry logic"

## Cross-Namespace Queries

Some queries benefit from searching multiple namespaces:

### "Authentication" Query

| Namespace | Expected Results |
|-----------|-----------------|
| decisions | "Use JWT for stateless auth" |
| learnings | "Refresh tokens need secure storage" |
| context | "Auth middleware in middleware/auth.py" |
| patterns | "Token validation pattern" |

### "Database" Query

| Namespace | Expected Results |
|-----------|-----------------|
| decisions | "PostgreSQL for JSONB support" |
| learnings | "Connection pooling prevents timeouts" |
| context | "Schema in models/, migrations in migrations/" |
| patterns | "Repository pattern for data access" |

## Namespace Selection Logic

When the query doesn't explicitly target a namespace:

```python
def infer_namespace(query):
    """Infer likely namespace from query patterns."""

    # Decision indicators
    if any(w in query.lower() for w in ['why', 'chose', 'decision', 'rationale']):
        return 'decisions'

    # Learning indicators
    if any(w in query.lower() for w in ['til', 'learned', 'discovered', 'gotcha']):
        return 'learnings'

    # Context indicators
    if any(w in query.lower() for w in ['where', 'location', 'file', 'directory']):
        return 'context'

    # Preference indicators
    if any(w in query.lower() for w in ['prefer', 'style', 'like', 'convention']):
        return 'preferences'

    # Pattern indicators
    if any(w in query.lower() for w in ['pattern', 'approach', 'idiom', 'how to']):
        return 'patterns'

    # Default: search all
    return None
```

## Lifecycle Considerations

Memories have different retention characteristics:

| Namespace | Typical Lifespan | Archive Trigger |
|-----------|------------------|-----------------|
| decisions | Project lifetime | Project completion |
| learnings | Long-term | Rarely archived |
| context | Can become stale | Project restructure |
| preferences | Long-term | User preference change |
| patterns | Long-term | Pattern superseded |

## Best Practices

1. **Be specific in queries**: "authentication jwt" better than "auth"
2. **Use namespace hints**: When you know the type you're looking for
3. **Cross-reference**: Important topics often span multiple namespaces
4. **Update stale context**: Mark outdated context as archived
5. **Link related memories**: Reference decision IDs in patterns
