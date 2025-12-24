# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.9.x   | :white_check_mark: |
| < 0.9   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

**DO NOT** open a public GitHub issue for security vulnerabilities.

Instead, please report vulnerabilities via one of these methods:

1. **GitHub Security Advisories** (Preferred)
   - Navigate to the [Security tab](../../security/advisories) of this repository
   - Click "Report a vulnerability"
   - Provide a detailed description

2. **Email**
   - Send details to the repository maintainers
   - Use the subject line: `[SECURITY] git-notes-memory vulnerability report`

### What to Include

Please include the following in your report:

- **Description**: Clear explanation of the vulnerability
- **Impact**: What an attacker could achieve
- **Affected versions**: Which versions are vulnerable
- **Steps to reproduce**: Detailed reproduction steps
- **Proof of concept**: Code or commands demonstrating the issue (if possible)
- **Suggested fix**: Your recommendations (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours of report
- **Initial assessment**: Within 7 days
- **Fix timeline**: Depends on severity
  - Critical: 7 days
  - High: 14 days
  - Medium: 30 days
  - Low: 60 days

### Disclosure Policy

- We will coordinate disclosure timing with the reporter
- Credit will be given to reporters (unless they prefer anonymity)
- We follow responsible disclosure practices

## Security Considerations

### Data Storage

- Memories are stored as git notes in your local repository
- SQLite index is stored in `~/.local/share/memory-plugin/` by default
- Sensitive data in memories is your responsibility to manage

### Best Practices

1. **Avoid storing secrets**: Do not capture API keys, passwords, or credentials as memories
2. **Review before sharing**: If sharing repositories with memories, review note contents first
3. **Secure your repository**: Standard git security practices apply
4. **Lock file permissions**: Lock files are created with 0o600 permissions

### Known Security Features

- Input validation on namespaces, summaries, and content
- Path traversal prevention in git operations
- No shell=True in subprocess calls
- File locking with timeout protection
- O_NOFOLLOW flag prevents symlink attacks on lock files

## Security Audit

This project underwent a security review on 2025-12-24 as part of the MAXALL code review process. Key findings were addressed:

- TOCTOU race condition mitigated with O_NOFOLLOW
- Subprocess timeouts added to prevent hangs
- Lock file permissions restricted to 0o600
- Thread safety added to service registry

For the full security assessment, see `docs/code-review/2025/12/24/CODE_REVIEW.md`.
