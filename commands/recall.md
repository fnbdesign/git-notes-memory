---
description: Recall relevant memories for the current context or a specific query
argument-hint: "[query] [--namespace=ns] [--limit=n]"
allowed-tools: ["Bash", "Read"]
---

# /memory:recall - Recall Relevant Memories

Retrieve relevant memories from the git-backed memory system.

## Your Task

You will help the user recall memories relevant to their current context or query.

### Step 1: Parse Arguments

**Arguments format**: `$ARGUMENTS`

Parse the arguments:
1. Extract `--namespace=<ns>` if present (one of: `decisions`, `learnings`, `context`, `preferences`, `patterns`)
2. Extract `--limit=<n>` if present (default: 5)
3. Everything else is the search query
4. If no query provided, use recent conversation context

### Step 2: Build Search Context

If query is empty:
- Extract key concepts from recent conversation (last 5-10 messages)
- Look for: file names, function names, error messages, technology terms
- Combine into a search query

### Step 3: Execute Search

Use Bash to invoke the Python library:

```bash
python3 -c "
from git_notes_memory import get_recall_service

recall = get_recall_service()
results = recall.search(
    query='''$QUERY''',
    namespace=$NAMESPACE,  # None for all namespaces
    limit=$LIMIT,
)

if not results:
    print('No relevant memories found.')
else:
    print(f'## Recalled Memories ({len(results)} results)\n')
    for i, r in enumerate(results, 1):
        print(f'### {i}. {r.namespace.title()}: {r.title or r.content[:50]}')
        print(f'**Relevance**: {r.score:.2f} | **Captured**: {r.created_at[:10]}')
        print(f'> {r.content[:200]}...\n')
"
```

Replace:
- `$QUERY` with the search query
- `$NAMESPACE` with `'$ns'` or `None`
- `$LIMIT` with the limit number

### Step 4: Present Results

Format the output as:

```
## Recalled Memories (3 results)

### 1. Decision: Use PostgreSQL for main database
**Relevance**: 0.92 | **Captured**: 2024-01-15
> Due to JSONB support and strong ecosystem for Python...

### 2. Learning: Connection pooling best practices
**Relevance**: 0.85 | **Captured**: 2024-01-10
> Always use connection pooling in production to prevent...

### 3. Context: Database schema location
**Relevance**: 0.78 | **Captured**: 2024-01-08
> Database migrations are in migrations/ directory...
```

If no results found:
```
No relevant memories found for your query.

**Tips**:
- Try a broader search term
- Use `/memory:search` for more options
- Check `/memory:status` to verify memories exist
```

## Namespace Reference

| Namespace | Contains |
|-----------|----------|
| `decisions` | Architectural and design decisions |
| `learnings` | Knowledge and discoveries |
| `context` | Project-specific information |
| `preferences` | User preferences and style |
| `patterns` | Recurring patterns and idioms |

## Examples

**User**: `/memory:recall database configuration`
**Action**: Search all namespaces for "database configuration"

**User**: `/memory:recall --namespace=decisions`
**Action**: Return recent decisions without specific query

**User**: `/memory:recall --limit=10 authentication`
**Action**: Search for "authentication" with 10 result limit

**User**: `/memory:recall`
**Action**: Extract context from recent conversation and search
