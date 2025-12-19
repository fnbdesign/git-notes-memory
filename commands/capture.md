---
description: Capture a memory (decision, learning, context, preference, or pattern) to the git-backed memory system
argument-hint: "[type] content to capture"
allowed-tools: ["Bash", "Write", "Read", "AskUserQuestion"]
---

# /memory:capture - Capture a Memory

Capture information to the git-backed memory system for later retrieval.

## Your Task

You will help the user capture a memory. The memory will be stored as a git note and indexed for semantic search.

### Step 1: Parse the Arguments

**Arguments format**: `$ARGUMENTS`

Parse the arguments:
1. If first word is a known type (`decision`, `learning`, `context`, `preference`, `pattern`), use it as the memory type
2. Everything else is the memory content
3. If no type specified, auto-detect based on content patterns:
   - Contains "decided", "chose", "will use" → `decision`
   - Contains "learned", "discovered", "TIL", "found out" → `learning`
   - Contains "remember", "note that", "keep in mind" → `context`
   - Contains "prefer", "always", "never", "should" → `preference`
   - Contains "pattern", "recurring", "often" → `pattern`
   - Default → `context`

### Step 2: Validate Content

If `$ARGUMENTS` is empty or very short (< 10 characters):
- Use AskUserQuestion to prompt for the memory content
- Question: "What would you like to capture?"
- Options: provide example prompts for each memory type

### Step 3: Capture the Memory

Use Bash to invoke the Python library:

```bash
python3 -c "
from git_notes_memory import get_capture_service

capture = get_capture_service()
memory = capture.capture_$TYPE(
    content='''$CONTENT''',
    source='command',
)
print(f'✅ Captured as {memory.namespace}: {memory.id[:8]}...')
print(f'   Summary: {memory.title or memory.content[:60]}...')
"
```

Replace:
- `$TYPE` with the memory type method: `capture_decision`, `capture_learning`, `capture_context`, `capture_preference`, `capture_pattern`
- `$CONTENT` with the user's content (escape quotes properly)

### Step 4: Confirm to User

Show the result:
```
✅ Memory captured!

**Type**: decision
**ID**: abc12345...
**Summary**: Use PostgreSQL for the main database...

This memory will be available for recall in future sessions.
Use `/memory:recall` to retrieve it.
```

## Memory Types Reference

| Type | Use For | Example |
|------|---------|---------|
| `decision` | Architectural or design decisions | "Use PostgreSQL for JSONB support" |
| `learning` | New knowledge or discoveries | "pytest fixtures can be module-scoped" |
| `context` | Project-specific information | "This project uses tabs for indentation" |
| `preference` | User preferences | "Prefer functional style over classes" |
| `pattern` | Recurring patterns | "Error handling follows Result pattern" |

## Error Handling

If the capture fails:
1. Check if we're in a git repository: `git rev-parse --git-dir`
2. Check if the library is installed: `python3 -c "import git_notes_memory"`
3. Show helpful error message with recovery action

## Examples

**User**: `/memory:capture decision Use Redis for session storage due to built-in expiration`
**Action**: Capture as decision type

**User**: `/memory:capture TIL you can use pytest -k to filter tests by name`
**Action**: Auto-detect as learning (contains "TIL")

**User**: `/memory:capture This project requires Python 3.10+`
**Action**: Auto-detect as context (general information)
