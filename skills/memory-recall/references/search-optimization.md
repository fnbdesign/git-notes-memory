# Search Optimization Techniques

Advanced techniques for optimizing memory recall queries.

## Query Expansion

Improve recall by expanding queries with related terms:

```python
from git_notes_memory import get_recall_service
from git_notes_memory.search import get_optimizer

recall = get_recall_service()
optimizer = get_optimizer()

# Original query
query = "database connection"

# Expanded with related terms
expanded = optimizer.expand_query(query)
# Result: "database connection pool timeout postgres sql"

results = recall.search(expanded, limit=10)
```

## Hybrid Search Strategy

Combine semantic and keyword search for best results:

```python
from git_notes_memory.search import get_optimizer

optimizer = get_optimizer()

# Hybrid search combines:
# 1. Vector similarity (semantic meaning)
# 2. BM25 keyword matching (exact terms)
# 3. Recency weighting (newer memories preferred)

results = optimizer.search(
    query="authentication JWT tokens",
    semantic_weight=0.6,  # 60% semantic
    keyword_weight=0.3,   # 30% keyword
    recency_weight=0.1,   # 10% recency
    limit=10
)
```

## Threshold Tuning

Adjust relevance thresholds based on context:

| Scenario | Threshold | Rationale |
|----------|-----------|-----------|
| Direct question | 0.8+ | High precision needed |
| Feature work | 0.6-0.7 | Balance precision/recall |
| Exploration | 0.5 | Cast wider net |
| Troubleshooting | 0.55 | Include related issues |

```python
# Dynamic threshold based on query type
def get_threshold(query_type):
    thresholds = {
        'question': 0.8,
        'feature': 0.65,
        'explore': 0.5,
        'debug': 0.55
    }
    return thresholds.get(query_type, 0.7)
```

## Namespace Filtering

Target specific memory types for faster, more relevant results:

```python
# For decision inquiries
results = recall.search(
    query="why redis",
    namespace="decisions",
    limit=5
)

# For troubleshooting
results = recall.search(
    query="timeout error",
    namespace="learnings",
    limit=10
)

# Multi-namespace search
results = recall.search(
    query="database",
    namespaces=["decisions", "patterns"],
    limit=10
)
```

## Context Window Management

Manage result size for context efficiency:

```python
# Summarize long memories
def format_for_context(memories, max_chars=500):
    formatted = []
    for m in memories:
        content = m.content
        if len(content) > max_chars:
            content = content[:max_chars] + "..."
        formatted.append({
            'type': m.namespace,
            'summary': m.title or content[:50],
            'score': m.score,
            'content': content
        })
    return formatted
```

## Caching Strategies

Cache frequent queries for faster recall:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query, namespace=None, limit=5):
    recall = get_recall_service()
    return recall.search(query, namespace=namespace, limit=limit)

# Clear cache when new memories added
def on_memory_captured():
    cached_search.cache_clear()
```

## Performance Metrics

Monitor search performance:

```python
import time

def timed_search(query, **kwargs):
    start = time.time()
    results = recall.search(query, **kwargs)
    duration = time.time() - start

    return {
        'results': results,
        'duration_ms': duration * 1000,
        'count': len(results),
        'avg_score': sum(r.score for r in results) / len(results) if results else 0
    }
```

## Best Practices

1. **Start specific, then broaden**: Begin with focused queries, expand if no results
2. **Use namespace hints**: When query implies a type (e.g., "why" → decisions)
3. **Limit results**: Surface 3-5 highly relevant memories, not all matches
4. **Cache common queries**: Project-specific terms are queried repeatedly
5. **Monitor relevance**: Track which recalled memories users actually reference
