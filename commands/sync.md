---
description: Synchronize the memory index with git notes
argument-hint: "[incremental|full|verify] [--repair] [--dry-run]"
allowed-tools: ["Bash", "Read"]
---

# /memory:sync - Synchronize Memory Index

Synchronize the local search index with git notes storage.

## Your Task

You will help the user synchronize or repair the memory index.

### Step 1: Parse Arguments

**Arguments format**: `$ARGUMENTS`

Parse the arguments:
1. First positional argument is mode: `incremental` (default), `full`, or `verify`
2. Extract `--repair` flag if present
3. Extract `--dry-run` flag if present

### Step 2: Execute Sync

Use Bash to invoke the Python library based on mode:

**Incremental Sync** (default):
```bash
python3 -c "
from git_notes_memory import get_sync_service

sync = get_sync_service()
stats = sync.incremental_sync()

print('## Sync Complete (Incremental)\n')
print('| Metric | Value |')
print('|--------|-------|')
print(f'| Notes scanned | {stats.get(\"scanned\", 0)} |')
print(f'| New indexed | {stats.get(\"added\", 0)} |')
print(f'| Updated | {stats.get(\"updated\", 0)} |')
print(f'| Removed | {stats.get(\"removed\", 0)} |')
print(f'| Errors | {stats.get(\"errors\", 0)} |')
print(f'| Duration | {stats.get(\"duration_ms\", 0)/1000:.2f}s |')
"
```

**Full Reindex**:
```bash
python3 -c "
from git_notes_memory import get_sync_service

sync = get_sync_service()
stats = sync.full_reindex()

print('## Sync Complete (Full Reindex)\n')
print('| Metric | Value |')
print('|--------|-------|')
print(f'| Notes scanned | {stats.get(\"scanned\", 0)} |')
print(f'| Indexed | {stats.get(\"indexed\", 0)} |')
print(f'| Errors | {stats.get(\"errors\", 0)} |')
print(f'| Duration | {stats.get(\"duration_ms\", 0)/1000:.2f}s |')
"
```

**Verify Consistency**:
```bash
python3 -c "
from git_notes_memory import get_sync_service

sync = get_sync_service()
report = sync.verify_consistency()

if report.get('consistent'):
    print('## Verification: ✅ Consistent\n')
    print(f'Index and git notes are in sync.')
    print(f'Total memories: {report.get(\"total\", 0)}')
else:
    print('## Verification: ⚠️ Inconsistencies Found\n')
    print('| Issue | Count |')
    print('|-------|-------|')
    print(f'| Missing from index | {len(report.get(\"missing_from_index\", []))} |')
    print(f'| Missing from git | {len(report.get(\"missing_from_git\", []))} |')
    print(f'| Out of sync | {len(report.get(\"out_of_sync\", []))} |')
    print('')
    print('Run `/memory:sync verify --repair` to fix issues.')
"
```

**Verify with Repair**:
```bash
python3 -c "
from git_notes_memory import get_sync_service

sync = get_sync_service()
report = sync.verify_and_repair()

print('## Repair Complete\n')
print('| Action | Count |')
print('|--------|-------|')
print(f'| Added to index | {report.get(\"added\", 0)} |')
print(f'| Removed from index | {report.get(\"removed\", 0)} |')
print(f'| Updated | {report.get(\"updated\", 0)} |')
print('')
print('Index is now consistent with git notes.')
"
```

### Step 3: Handle Dry Run

If `--dry-run` is specified, show what would happen without making changes:
```bash
python3 -c "
from git_notes_memory import get_sync_service

sync = get_sync_service()
plan = sync.plan_sync()  # Returns what would be done

print('## Dry Run - No Changes Made\n')
print('**Would perform:**')
print(f'- Add {plan.get(\"to_add\", 0)} memories to index')
print(f'- Update {plan.get(\"to_update\", 0)} memories')
print(f'- Remove {plan.get(\"to_remove\", 0)} orphaned entries')
print('')
print('Run without --dry-run to apply changes.')
"
```

## When to Use Each Mode

| Mode | When to Use |
|------|-------------|
| `incremental` | After normal use, quick sync of new changes |
| `full` | After major changes, index seems corrupted |
| `verify` | To check consistency without changes |
| `verify --repair` | To fix detected inconsistencies |

## Examples

**User**: `/memory:sync`
**Action**: Run incremental sync (default)

**User**: `/memory:sync full`
**Action**: Complete reindex from scratch

**User**: `/memory:sync verify`
**Action**: Check for inconsistencies

**User**: `/memory:sync verify --repair`
**Action**: Fix any inconsistencies found

**User**: `/memory:sync full --dry-run`
**Action**: Show what full reindex would do
