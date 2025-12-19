"""Utility functions for the memory capture system.

Provides shared utilities for:
- Temporal decay calculations for memory relevance
- Timestamp parsing and age calculations
- Input validation helpers

All functions are pure and stateless where possible.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime

from git_notes_memory.config import (
    MAX_CONTENT_BYTES,
    MAX_SUMMARY_CHARS,
    NAMESPACES,
    SECONDS_PER_DAY,
)

__all__ = [
    # Temporal Decay
    "calculate_temporal_decay",
    "calculate_age_days",
    # Timestamp Parsing
    "parse_iso_timestamp",
    "parse_iso_timestamp_safe",
    # Validation
    "validate_namespace",
    "validate_content_size",
    "validate_summary_length",
    "validate_git_ref",
    "is_valid_namespace",
    "is_valid_git_ref",
]


# =============================================================================
# Temporal Decay Functions
# =============================================================================


def calculate_temporal_decay(
    timestamp: datetime | None,
    half_life_days: float = 30.0,
    min_decay: float | None = None,
) -> float:
    """Calculate temporal decay using exponential decay formula.

    Uses the formula: decay = 2^(-age_days / half_life_days)

    This models how memory relevance decreases over time:
    - At age 0: decay = 1.0 (fully relevant)
    - At age = half_life_days: decay = 0.5 (half as relevant)
    - At age = 2 * half_life_days: decay = 0.25
    - And so on...

    Args:
        timestamp: The timestamp to calculate decay from. If None, returns 0.5.
        half_life_days: Time in days for relevance to decay by half. Default 30.
        min_decay: Optional minimum decay value (floor). If provided, result
            will never be less than this value.

    Returns:
        Decay factor between 0.0 and 1.0 (or min_decay and 1.0 if specified).

    Examples:
        >>> from datetime import datetime, UTC, timedelta
        >>> now = datetime.now(UTC)
        >>> calculate_temporal_decay(now)  # Just created
        1.0
        >>> calculate_temporal_decay(now - timedelta(days=30))  # 30 days old
        0.5
        >>> calculate_temporal_decay(None)  # No timestamp
        0.5
    """
    if timestamp is None:
        return 0.5

    now = datetime.now(UTC)

    # Ensure timestamp is timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    age = now - timestamp
    age_days = age.total_seconds() / SECONDS_PER_DAY

    # Handle negative age (future timestamp) gracefully
    if age_days < 0:
        age_days = 0

    decay = math.pow(2, -age_days / half_life_days)

    if min_decay is not None:
        return max(min_decay, decay)

    return decay


def calculate_age_days(timestamp: datetime | None) -> float:
    """Calculate the age in days from a timestamp.

    Args:
        timestamp: The timestamp to calculate age from. If None, returns 0.0.

    Returns:
        Age in days as a float. Returns 0.0 for None or future timestamps.

    Examples:
        >>> from datetime import datetime, UTC, timedelta
        >>> now = datetime.now(UTC)
        >>> calculate_age_days(now)  # Just now
        0.0
        >>> calculate_age_days(now - timedelta(days=7))  # 7 days ago
        7.0
    """
    if timestamp is None:
        return 0.0

    now = datetime.now(UTC)

    # Ensure timestamp is timezone-aware
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)

    age = now - timestamp
    age_days = age.total_seconds() / SECONDS_PER_DAY

    # Never return negative age
    return max(0.0, age_days)


# =============================================================================
# Timestamp Parsing Functions
# =============================================================================


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """Parse an ISO 8601 timestamp string to datetime.

    Handles both 'Z' suffix (Zulu time) and explicit timezone offsets.
    The returned datetime is always timezone-aware.

    Args:
        timestamp_str: ISO 8601 formatted timestamp string.
            Examples: "2024-01-15T10:30:00Z", "2024-01-15T10:30:00+00:00"

    Returns:
        Timezone-aware datetime object.

    Raises:
        ValueError: If the timestamp string is not valid ISO 8601 format.

    Examples:
        >>> parse_iso_timestamp("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        >>> parse_iso_timestamp("2024-01-15T10:30:00+05:30")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=...)
    """
    # Convert 'Z' suffix to explicit UTC offset for fromisoformat
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"

    return datetime.fromisoformat(timestamp_str)


def parse_iso_timestamp_safe(timestamp_str: str | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string safely, returning None on error.

    A safe wrapper around parse_iso_timestamp that catches parsing errors
    and returns None instead of raising exceptions.

    Args:
        timestamp_str: ISO 8601 formatted timestamp string, or None.

    Returns:
        Timezone-aware datetime object, or None if parsing fails or input is None.

    Examples:
        >>> parse_iso_timestamp_safe("2024-01-15T10:30:00Z")
        datetime.datetime(2024, 1, 15, 10, 30, tzinfo=datetime.timezone.utc)
        >>> parse_iso_timestamp_safe("invalid")
        None
        >>> parse_iso_timestamp_safe(None)
        None
    """
    if timestamp_str is None:
        return None

    try:
        return parse_iso_timestamp(timestamp_str)
    except (ValueError, TypeError):
        return None


# =============================================================================
# Validation Functions
# =============================================================================

# Pattern for valid git refs (no shell metacharacters or path traversal)
_GIT_REF_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")

# Disallowed sequences in git refs
_DISALLOWED_SEQUENCES = frozenset(
    {
        "..",  # Path traversal
        "//",  # Double slash
        "@{",  # Reflog syntax
        "~",  # Ancestor reference (allow in some contexts)
        "^",  # Parent reference (allow in some contexts)
        ":",  # Pathspec separator
        "?",  # Shell glob
        "*",  # Shell glob
        "[",  # Shell glob
        "\\",  # Backslash
        " ",  # Space
    }
)


def is_valid_namespace(namespace: str) -> bool:
    """Check if a namespace is valid.

    Args:
        namespace: The namespace to validate.

    Returns:
        True if the namespace is in NAMESPACES, False otherwise.
    """
    return namespace in NAMESPACES


def validate_namespace(namespace: str) -> None:
    """Validate that a namespace is allowed.

    Args:
        namespace: The namespace to validate.

    Raises:
        ValueError: If the namespace is not in NAMESPACES.
    """
    if not is_valid_namespace(namespace):
        valid = ", ".join(sorted(NAMESPACES))
        raise ValueError(f"Invalid namespace '{namespace}'. Must be one of: {valid}")


def validate_content_size(content: str | bytes) -> None:
    """Validate that content does not exceed maximum size.

    Args:
        content: The content to validate (string or bytes).

    Raises:
        ValueError: If content exceeds MAX_CONTENT_BYTES (100KB).
    """
    if isinstance(content, str):
        size = len(content.encode("utf-8"))
    else:
        size = len(content)

    if size > MAX_CONTENT_BYTES:
        raise ValueError(
            f"Content size ({size} bytes) exceeds maximum "
            f"({MAX_CONTENT_BYTES} bytes / 100KB)"
        )


def validate_summary_length(summary: str) -> None:
    """Validate that summary does not exceed maximum length.

    Args:
        summary: The summary to validate.

    Raises:
        ValueError: If summary exceeds MAX_SUMMARY_CHARS (100 characters).
    """
    if len(summary) > MAX_SUMMARY_CHARS:
        raise ValueError(
            f"Summary length ({len(summary)} chars) exceeds maximum "
            f"({MAX_SUMMARY_CHARS} chars)"
        )


def is_valid_git_ref(ref: str) -> bool:
    """Check if a git ref is valid and safe.

    Validates that the ref:
    - Contains only allowed characters (alphanumeric, ., _, /, -)
    - Does not contain path traversal sequences
    - Does not contain shell metacharacters

    Args:
        ref: The git ref to validate.

    Returns:
        True if the ref is valid and safe, False otherwise.
    """
    if not ref:
        return False

    # Check basic pattern
    if not _GIT_REF_PATTERN.match(ref):
        return False

    # Check for disallowed sequences
    for seq in _DISALLOWED_SEQUENCES:
        if seq in ref:
            return False

    # Additional checks
    if ref.startswith(".") or ref.endswith("."):
        return False
    if ref.startswith("/") or ref.endswith("/"):
        return False

    return not ref.endswith(".lock")


def validate_git_ref(ref: str) -> None:
    """Validate that a git ref is safe to use.

    Args:
        ref: The git ref to validate.

    Raises:
        ValueError: If the ref contains unsafe characters or sequences.
    """
    if not is_valid_git_ref(ref):
        raise ValueError(
            f"Invalid git ref '{ref}'. Refs must not contain shell "
            "metacharacters, path traversal sequences, or special git syntax."
        )
