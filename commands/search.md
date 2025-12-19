---
description: Search memories with advanced filtering options
argument-hint: "<query> [--type=semantic|keyword|hybrid] [--namespace=ns] [--since=date] [--limit=n]"
allowed-tools: ["Bash", "Read"]
---

# /memory:search - Advanced Memory Search

Search memories with advanced filtering and search options.

## Your Task

You will help the user search memories with precise control over search behavior.

### Step 1: Parse Arguments

**Arguments format**: `$ARGUMENTS`

Parse the arguments:
1. Extract `--type=<type>` if present: `semantic`, `keyword`, or `hybrid` (default: `hybrid`)
2. Extract `--namespace=<ns>` if present
3. Extract `--since=<date>` if present (YYYY-MM-DD format)
4. Extract `--until=<date>` if present
5. Extract `--tags=<tags>` if present (comma-separated)
6. Extract `--limit=<n>` if present (default: 10)
7. Extract `--verbose` flag if present
8. Everything else is the search query

If query is missing, use AskUserQuestion to prompt for it.

### Step 2: Execute Search

Use Bash to invoke the Python library:

```bash
python3 -c "
from git_notes_memory import get_recall_service
from git_notes_memory.search import get_optimizer

recall = get_recall_service()
optimizer = get_optimizer()

# Perform search based on type
query = '''$QUERY'''
search_type = '$TYPE'  # semantic, keyword, or hybrid

if search_type == 'semantic':
    results = recall.semantic_search(query, limit=$LIMIT)
elif search_type == 'keyword':
    results = recall.text_search(query, limit=$LIMIT)
else:  # hybrid
    results = optimizer.search(query, limit=$LIMIT)

# Apply filters
$NAMESPACE_FILTER
$DATE_FILTER
$TAG_FILTER

# Output results
print(f'## Search Results for \"{query}\" ({len(results)} found)\n')
print('| # | Type | Summary | Relevance | Date |')
print('|---|------|---------|-----------|------|')
for i, r in enumerate(results, 1):
    summary = (r.title or r.content[:40]).replace('|', '\\|')
    print(f'| {i} | {r.namespace} | {summary} | {r.score:.2f} | {r.created_at[:10]} |')

$VERBOSE_OUTPUT
"
```

### Step 3: Present Results

**Standard output** (table format):
```
## Search Results for "authentication" (5 found)

| # | Type | Summary | Relevance | Date |
|---|------|---------|-----------|------|
| 1 | decision | Use JWT for API auth | 0.94 | 2024-01-15 |
| 2 | learning | OAuth2 flow patterns | 0.89 | 2024-01-12 |
| 3 | context | Auth middleware location | 0.82 | 2024-01-10 |
| 4 | preference | Prefer httpOnly cookies | 0.78 | 2024-01-08 |
| 5 | pattern | Token refresh pattern | 0.75 | 2024-01-05 |
```

**Verbose output** (includes full content):
```
### 1. Decision: Use JWT for API auth
**Relevance**: 0.94 | **Date**: 2024-01-15 | **Tags**: auth, api

> We decided to use JWT tokens for API authentication because:
> - Stateless authentication reduces server load
> - Easy to validate without database lookup
> - Built-in expiration support
>
> Implementation: Use PyJWT library with RS256 signing.
```

## Search Types Explained

| Type | Description | Best For |
|------|-------------|----------|
| `semantic` | Vector similarity search | Conceptual queries, finding related ideas |
| `keyword` | Traditional text matching | Exact terms, specific identifiers |
| `hybrid` | Combines both approaches | General use, best results |

## Examples

**User**: `/memory:search "authentication patterns" --type=semantic`
**Action**: Find conceptually similar memories about authentication

**User**: `/memory:search pytest --namespace=learnings --since=2024-01-01`
**Action**: Find learnings about pytest from this year

**User**: `/memory:search database --tags=postgresql,performance --verbose`
**Action**: Find tagged memories with full content

**User**: `/memory:search "API design" --limit=20`
**Action**: Return up to 20 results for API design
