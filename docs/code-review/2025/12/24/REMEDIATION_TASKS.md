# Remediation Tasks

Generated from MAXALL code review on 2025-12-24.

---

## 🔴 Critical (Fix Immediately)

### CRIT-001: Blocking Lock Without Timeout ✅
- **File:** `src/git_notes_memory/capture.py:87`
- **Task:** Implement non-blocking lock with retry loop and timeout
- **Code:**
```python
import time
deadline = time.monotonic() + timeout
while True:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        if time.monotonic() >= deadline:
            raise CaptureError("Lock acquisition timed out")
        time.sleep(0.1)
```
- [x] Implemented
- [x] Tested
- [x] Verified

### CRIT-002: Missing repo_path in insert_batch ✅
- **File:** `src/git_notes_memory/index.py:468-497`
- **Task:** Add `repo_path` column and value to INSERT statement
- [x] Implemented
- [x] Tested
- [x] Verified

### CRIT-003: No PII Detection (Deferred to Backlog)
- **File:** `src/git_notes_memory/capture.py:329-380`
- **Task:** Add PII detection warnings (can be implemented incrementally)
- **Note:** Move to backlog - requires design decision on detection scope
- [ ] Design reviewed
- [ ] Implemented
- [ ] Tested

---

## 🟠 High Priority (Before Next Release)

### Security

- [x] `capture.py:76-102` Add O_NOFOLLOW to prevent symlink attacks - HIGH-005 ✅
- [ ] `git_ops.py:44-84` Reject @ and : in path validation - HIGH-006
- [x] Create SECURITY.md with vulnerability reporting process - HIGH-014 ✅

### Performance

- [x] `git_ops.py:138-143` Add timeout=30 to subprocess.run() - HIGH-001 ✅
- [ ] `recall.py:574` Batch git operations with git cat-file --batch - HIGH-002
- [ ] `embedding.py:202` Document prewarm strategy for cold starts - HIGH-003
- [ ] `sync.py:306-327` Process in chunks of 1000 - HIGH-004

### Concurrency

- [x] `index.py:188-191` Add threading.Lock around transactions - HIGH-011 ✅
- [x] `registry.py:56-95` Add threading.Lock to get() method - HIGH-012 ✅

### Compliance

- [ ] Add data retention policy with expires_at column - HIGH-008
- [ ] Add delete_by_pattern() and purge_all() for DSAR - HIGH-009
- [ ] Implement JSON audit log for capture/recall - HIGH-010

### Plugin

- [ ] Create hooks/templates/guidance_minimal.md - HIGH-015
- [ ] Create hooks/templates/guidance_standard.md - HIGH-015
- [ ] Create hooks/templates/guidance_detailed.md - HIGH-015

---

## 🟡 Medium Priority (Next Sprint)

### Database Optimization

- [x] `index.py:186` Enable WAL mode: `PRAGMA journal_mode=WAL` - MED-005 ✅
- [ ] `index.py` Add composite index idx_memories_ns_spec_ts - MED-003
- [ ] `index.py` Add composite index idx_memories_status_timestamp - MED-006
- [ ] `sync.py:164` Use INSERT OR REPLACE instead of exists check - MED-002

### Security Hardening

- [x] `capture.py:81` Change lock file permissions to 0o600 - MED-001 ✅
- [ ] `signal_detector.py` Restructure ReDoS-prone patterns - MED-007
- [ ] `note_parser.py` Add DepthLimitedLoader for YAML - MED-008

### Resilience

- [ ] `index.py:252` Track migration version atomically - MED-009
- [ ] `embedding.py:145` Set TRANSFORMERS_OFFLINE after first download - MED-010
- [ ] `index.py:170` Detect corruption and auto-rebuild - MED-011
- [ ] `hook_utils.py:219` Add threading.Timer fallback for Windows - MED-012
- [ ] `capture.py:474` Add repair marker on index failure - MED-013

### Architecture

- [ ] `index.py` Extract SearchService from IndexService - MED-014
- [ ] `capture.py` Extract ValidationService from CaptureService - MED-015
- [ ] `sync.py` Replace bare except with specific exceptions - MED-016
- [ ] `capture.py` Extract ContentBuilder helper - MED-017
- [ ] Multiple files - Create base service factory - MED-018
- [ ] Various - Move hardcoded values to config.py - MED-019

### Documentation

- [ ] Create data flow documentation diagram - MED-020
- [ ] Add tests for hook handlers (target 70%+) - MED-021
- [x] Create CHANGELOG.md - MED-022 ✅
- [ ] Update .env.example with HOOK_* variables - MED-023

### Plugin

- [ ] `hooks/precompact.py:40` Output `{"continue": true}` - MED-024

---

## 🟢 Low Priority (Backlog)

### Database

- [ ] Document vector search over-fetching behavior - LOW-001
- [ ] WHERE 1=1 pattern (cosmetic, no action) - LOW-002
- [ ] Document connection pooling for high concurrency - LOW-003
- [ ] SQL placeholder documentation - LOW-004
- [ ] Run VACUUM after bulk deletes - LOW-009

### Security

- [ ] Improve path sanitization in error messages - LOW-005
- [ ] Load .env from trusted locations only - LOW-006
- [ ] XML escaping (informational, already correct) - LOW-007
- [ ] Document file descriptor management - LOW-008

### Plugin

- [ ] Document session start guidance toggle - LOW-010
- [ ] Shorten skill descriptions to <100 chars - LOW-011
- [ ] Add version requirements to skills - LOW-012
- [ ] Add optional fields to plugin.json - LOW-013
- [ ] Standardize argument-hint syntax - LOW-014
- [ ] Add tool documentation to commands - LOW-015
- [ ] Fix conflicting API examples in skills - LOW-016

### Testing

- [ ] Create tests/test_hook_utils.py - LOW-017
- [ ] Create tests/test_session_analyzer.py - LOW-018

---

## Summary

| Priority | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| 🔴 Critical | 3 | 2 | 1 (deferred) |
| 🟠 High | 15 | 5 | 10 |
| 🟡 Medium | 24 | 3 | 21 |
| 🟢 Low | 18 | 0 | 18 |
| **Total** | **60** | **10** | **50** |

**MAXALL Remediation Status**: 10 fixes implemented and verified (2025-12-24)

---

## MAXALL Mode: Auto-Remediation

In MAXALL mode, the following items will be automatically remediated:

### Phase 1: Critical Fixes
1. ✅ CRIT-001: Lock timeout implementation
2. ✅ CRIT-002: insert_batch repo_path fix

### Phase 2: High Priority
3. ✅ HIGH-001: Subprocess timeout
4. ✅ HIGH-005: TOCTOU O_NOFOLLOW
5. ✅ MED-001: Lock file permissions
6. ✅ MED-005: WAL mode
7. ✅ HIGH-011: Threading lock for IndexService
8. ✅ HIGH-012: Threading lock for ServiceRegistry

### Phase 3: Documentation
9. ✅ HIGH-014: SECURITY.md
10. ✅ MED-022: CHANGELOG.md

### Deferred (Requires Design Decision)
- CRIT-003: PII detection (needs scope definition)
- MED-014/015: God class refactoring (needs architecture review)
- HIGH-008/009: Data retention (needs policy definition)

---

*Report: [CODE_REVIEW.md](./CODE_REVIEW.md)*
*Summary: [REVIEW_SUMMARY.md](./REVIEW_SUMMARY.md)*
