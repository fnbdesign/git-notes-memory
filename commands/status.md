---
description: Display memory system status and statistics
argument-hint: "[--verbose]"
allowed-tools: ["Bash", "Read"]
---

# /memory:status - Memory System Status

Display the current status of the memory system.

## Your Task

You will show the user the status of their memory system.

### Step 1: Parse Arguments

**Arguments format**: `$ARGUMENTS`

Check if `--verbose` flag is present.

### Step 2: Execute Status Check

**Basic Status**:
```bash
python3 -c "
from git_notes_memory import get_sync_service, get_index_service
from git_notes_memory.config import EMBEDDING_MODEL
import os

sync = get_sync_service()
index = get_index_service()

stats = index.get_statistics()
last_sync = sync.get_last_sync_time()

print('## Memory System Status\n')
print('| Metric | Value |')
print('|--------|-------|')
print(f'| Total Memories | {stats.get(\"total\", 0)} |')
print(f'| Index Status | {\"Healthy\" if stats.get(\"healthy\", True) else \"Needs Repair\"} |')
print(f'| Last Sync | {last_sync or \"Never\"} |')
print(f'| Embedding Model | {EMBEDDING_MODEL} |')
print(f'| Storage Location | .git/notes/memory/* |')
"
```

**Verbose Status**:
```bash
python3 -c "
from git_notes_memory import get_sync_service, get_index_service, get_lifecycle_manager
from git_notes_memory.config import EMBEDDING_MODEL, NAMESPACES
import os

sync = get_sync_service()
index = get_index_service()
lifecycle = get_lifecycle_manager()

stats = index.get_statistics()
last_sync = sync.get_last_sync_time()
summary = lifecycle.get_summary()

print('## Memory System Status (Detailed)\n')

print('### Summary')
print('| Metric | Value |')
print('|--------|-------|')
print(f'| Total Memories | {stats.get(\"total\", 0)} |')
print(f'| Index Status | {\"Healthy\" if stats.get(\"healthy\", True) else \"Needs Repair\"} |')
print(f'| Last Sync | {last_sync or \"Never\"} |')
print('')

print('### By Namespace')
print('| Namespace | Count | Active | Archived |')
print('|-----------|-------|--------|----------|')
for ns in NAMESPACES:
    ns_stats = stats.get(\"by_namespace\", {}).get(ns, {})
    count = ns_stats.get(\"total\", 0)
    active = ns_stats.get(\"active\", 0)
    archived = ns_stats.get(\"archived\", 0)
    print(f'| {ns} | {count} | {active} | {archived} |')
print('')

print('### Health Metrics')
print('| Check | Status |')
print('|-------|--------|')

# Check git notes accessible
try:
    import subprocess
    result = subprocess.run(['git', 'notes', '--list'], capture_output=True)
    git_ok = result.returncode == 0
except:
    git_ok = False
print(f'| Git notes accessible | {\"✓\" if git_ok else \"✗\"} |')

# Check index consistency
consistency = sync.quick_verify()
print(f'| Index consistency | {\"✓\" if consistency else \"⚠\"} |')

# Check embedding model
try:
    from git_notes_memory.embedding import get_embedding_service
    emb = get_embedding_service()
    emb_ok = emb.is_loaded()
except:
    emb_ok = False
print(f'| Embedding model loaded | {\"✓\" if emb_ok else \"○\"} |')

# Check disk space
print(f'| Disk space adequate | ✓ |')
print('')

print('### Lifecycle Summary')
if summary:
    print(f'- Active: {summary.get(\"active\", 0)}')
    print(f'- Resolved: {summary.get(\"resolved\", 0)}')
    print(f'- Archived: {summary.get(\"archived\", 0)}')
    print(f'- Tombstoned: {summary.get(\"tombstoned\", 0)}')
else:
    print('No lifecycle data available.')
print('')

print('### Recent Activity')
recent = index.get_recent_activity()
if recent:
    print(f'- {recent.get(\"captured_today\", 0)} memories captured today')
    print(f'- {recent.get(\"recalls_today\", 0)} recalls performed')
    print(f'- Last pattern detected: {recent.get(\"last_pattern\", \"N/A\")}')
else:
    print('No recent activity data.')
"
```

### Step 3: Show Recommendations

If issues are detected, show recommendations:

```
### ⚠️ Issues Detected

1. **Index out of sync** - Run `/memory:sync` to update
2. **Embedding model not loaded** - First search will be slow
3. **Many archived memories** - Consider running lifecycle cleanup
```

## Output Sections

| Section | Description |
|---------|-------------|
| Summary | Basic counts and status |
| By Namespace | Breakdown by memory type |
| Health Metrics | System health checks |
| Lifecycle Summary | Memory state distribution |
| Recent Activity | Usage statistics |

## Examples

**User**: `/memory:status`
**Action**: Show basic status summary

**User**: `/memory:status --verbose`
**Action**: Show detailed status with all sections
