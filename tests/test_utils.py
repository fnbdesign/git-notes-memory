"""Tests for git_notes_memory.utils module.

Tests all utility functions including temporal decay, timestamp parsing,
and validation helpers with comprehensive edge cases.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from git_notes_memory import config, utils

if TYPE_CHECKING:
    pass


# =============================================================================
# Temporal Decay Tests
# =============================================================================


class TestCalculateTemporalDecay:
    """Tests for calculate_temporal_decay function."""

    def test_decay_at_zero_age(self) -> None:
        """Test that decay is 1.0 for timestamp equal to now."""
        now = datetime.now(UTC)
        decay = utils.calculate_temporal_decay(now)
        assert decay == pytest.approx(1.0, abs=0.01)

    def test_decay_at_half_life(self) -> None:
        """Test that decay is 0.5 at exactly half_life_days."""
        now = datetime.now(UTC)
        half_life = 30.0
        timestamp = now - timedelta(days=half_life)
        decay = utils.calculate_temporal_decay(timestamp, half_life_days=half_life)
        assert decay == pytest.approx(0.5, abs=0.01)

    def test_decay_at_two_half_lives(self) -> None:
        """Test that decay is 0.25 at two half-lives."""
        now = datetime.now(UTC)
        half_life = 30.0
        timestamp = now - timedelta(days=half_life * 2)
        decay = utils.calculate_temporal_decay(timestamp, half_life_days=half_life)
        assert decay == pytest.approx(0.25, abs=0.01)

    def test_decay_none_timestamp(self) -> None:
        """Test that None timestamp returns 0.5."""
        decay = utils.calculate_temporal_decay(None)
        assert decay == 0.5

    def test_decay_custom_half_life(self) -> None:
        """Test decay with custom half-life."""
        now = datetime.now(UTC)
        half_life = 7.0  # One week
        timestamp = now - timedelta(days=7)
        decay = utils.calculate_temporal_decay(timestamp, half_life_days=half_life)
        assert decay == pytest.approx(0.5, abs=0.01)

    def test_decay_with_min_decay(self) -> None:
        """Test that min_decay provides a floor for decay value."""
        now = datetime.now(UTC)
        # Very old timestamp
        timestamp = now - timedelta(days=365)
        decay = utils.calculate_temporal_decay(timestamp, min_decay=0.1)
        assert decay >= 0.1

    def test_decay_old_timestamp_without_min(self) -> None:
        """Test decay for very old timestamp without min_decay."""
        now = datetime.now(UTC)
        timestamp = now - timedelta(days=365)
        decay = utils.calculate_temporal_decay(timestamp, half_life_days=30.0)
        # After ~365 days with 30-day half-life: 2^(-365/30) ≈ 0.00015
        assert decay < 0.01
        assert decay > 0.0

    def test_decay_naive_datetime_converted(self) -> None:
        """Test that naive datetime is converted to UTC."""
        # Create naive datetime (no timezone)
        now = datetime.now(UTC)
        naive = datetime(now.year, now.month, now.day, now.hour, now.minute)
        decay = utils.calculate_temporal_decay(naive)
        # Should still work and return approximately 1.0
        assert decay == pytest.approx(1.0, abs=0.1)

    def test_decay_future_timestamp_clamped(self) -> None:
        """Test that future timestamps are treated as age 0."""
        now = datetime.now(UTC)
        future = now + timedelta(days=10)
        decay = utils.calculate_temporal_decay(future)
        assert decay == 1.0

    def test_decay_decreases_over_time(self) -> None:
        """Test that decay decreases monotonically over time."""
        now = datetime.now(UTC)
        decays = []
        for days in [0, 7, 14, 30, 60, 90]:
            timestamp = now - timedelta(days=days)
            decays.append(utils.calculate_temporal_decay(timestamp))

        # Each subsequent decay should be less than the previous
        for i in range(1, len(decays)):
            assert decays[i] < decays[i - 1]

    def test_decay_formula_correctness(self) -> None:
        """Test the exact decay formula: 2^(-age_days / half_life_days)."""
        now = datetime.now(UTC)
        half_life = 30.0

        for days in [15, 45, 60, 90]:
            timestamp = now - timedelta(days=days)
            decay = utils.calculate_temporal_decay(timestamp, half_life_days=half_life)
            expected = math.pow(2, -days / half_life)
            assert decay == pytest.approx(expected, abs=0.01)


class TestCalculateAgeDays:
    """Tests for calculate_age_days function."""

    def test_age_now_is_zero(self) -> None:
        """Test that current timestamp has age close to 0."""
        now = datetime.now(UTC)
        age = utils.calculate_age_days(now)
        assert age == pytest.approx(0.0, abs=0.01)

    def test_age_one_day(self) -> None:
        """Test age calculation for one day ago."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        age = utils.calculate_age_days(yesterday)
        assert age == pytest.approx(1.0, abs=0.01)

    def test_age_one_week(self) -> None:
        """Test age calculation for one week ago."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)
        age = utils.calculate_age_days(week_ago)
        assert age == pytest.approx(7.0, abs=0.01)

    def test_age_none_is_zero(self) -> None:
        """Test that None timestamp returns 0.0."""
        age = utils.calculate_age_days(None)
        assert age == 0.0

    def test_age_future_is_zero(self) -> None:
        """Test that future timestamps return 0.0."""
        now = datetime.now(UTC)
        future = now + timedelta(days=10)
        age = utils.calculate_age_days(future)
        assert age == 0.0

    def test_age_naive_datetime_converted(self) -> None:
        """Test that naive datetime is converted to UTC."""
        now = datetime.now(UTC)
        one_day_ago = now - timedelta(days=1)
        naive = datetime(
            one_day_ago.year,
            one_day_ago.month,
            one_day_ago.day,
            one_day_ago.hour,
            one_day_ago.minute,
        )
        age = utils.calculate_age_days(naive)
        assert age == pytest.approx(1.0, abs=0.1)

    def test_age_fractional_days(self) -> None:
        """Test age calculation with fractional days."""
        now = datetime.now(UTC)
        twelve_hours_ago = now - timedelta(hours=12)
        age = utils.calculate_age_days(twelve_hours_ago)
        assert age == pytest.approx(0.5, abs=0.01)


# =============================================================================
# Timestamp Parsing Tests
# =============================================================================


class TestParseIsoTimestamp:
    """Tests for parse_iso_timestamp function."""

    def test_parse_z_suffix(self) -> None:
        """Test parsing timestamp with Z suffix."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0
        assert result.tzinfo is not None

    def test_parse_explicit_utc_offset(self) -> None:
        """Test parsing timestamp with +00:00 offset."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00+00:00")
        assert result.year == 2024
        assert result.tzinfo is not None

    def test_parse_positive_offset(self) -> None:
        """Test parsing timestamp with positive timezone offset."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00+05:30")
        assert result.year == 2024
        assert result.tzinfo is not None
        # Verify offset
        offset = result.utcoffset()
        assert offset is not None
        assert offset == timedelta(hours=5, minutes=30)

    def test_parse_negative_offset(self) -> None:
        """Test parsing timestamp with negative timezone offset."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00-08:00")
        assert result.year == 2024
        offset = result.utcoffset()
        assert offset is not None
        assert offset == timedelta(hours=-8)

    def test_parse_with_microseconds(self) -> None:
        """Test parsing timestamp with microseconds."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00.123456Z")
        assert result.microsecond == 123456

    def test_parse_with_milliseconds(self) -> None:
        """Test parsing timestamp with milliseconds."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00.123Z")
        assert result.microsecond == 123000

    def test_parse_invalid_format_raises(self) -> None:
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError):
            utils.parse_iso_timestamp("not-a-timestamp")

    def test_parse_empty_string_raises(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError):
            utils.parse_iso_timestamp("")

    def test_parse_date_only_works(self) -> None:
        """Test that date-only string is parsed (Python 3.11+ behavior)."""
        # Python 3.11+ accepts date-only strings in fromisoformat
        result = utils.parse_iso_timestamp("2024-01-15")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_timezone_aware(self) -> None:
        """Test that result is always timezone-aware."""
        result = utils.parse_iso_timestamp("2024-01-15T10:30:00Z")
        assert result.tzinfo is not None


class TestParseIsoTimestampSafe:
    """Tests for parse_iso_timestamp_safe function."""

    def test_safe_parse_valid(self) -> None:
        """Test safe parsing of valid timestamp."""
        result = utils.parse_iso_timestamp_safe("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024

    def test_safe_parse_none_returns_none(self) -> None:
        """Test that None input returns None."""
        result = utils.parse_iso_timestamp_safe(None)
        assert result is None

    def test_safe_parse_invalid_returns_none(self) -> None:
        """Test that invalid input returns None."""
        result = utils.parse_iso_timestamp_safe("invalid")
        assert result is None

    def test_safe_parse_empty_returns_none(self) -> None:
        """Test that empty string returns None."""
        result = utils.parse_iso_timestamp_safe("")
        assert result is None

    def test_safe_parse_malformed_returns_none(self) -> None:
        """Test that malformed timestamp returns None."""
        result = utils.parse_iso_timestamp_safe("2024-13-45T99:99:99Z")
        assert result is None


# =============================================================================
# Namespace Validation Tests
# =============================================================================


class TestIsValidNamespace:
    """Tests for is_valid_namespace function."""

    def test_valid_namespaces(self) -> None:
        """Test all valid namespaces return True."""
        for ns in config.NAMESPACES:
            assert utils.is_valid_namespace(ns) is True

    def test_invalid_namespace(self) -> None:
        """Test invalid namespace returns False."""
        assert utils.is_valid_namespace("invalid") is False

    def test_empty_namespace(self) -> None:
        """Test empty string returns False."""
        assert utils.is_valid_namespace("") is False

    def test_case_sensitive(self) -> None:
        """Test namespace validation is case-sensitive."""
        assert utils.is_valid_namespace("INCEPTION") is False
        assert utils.is_valid_namespace("Inception") is False
        assert utils.is_valid_namespace("inception") is True


class TestValidateNamespace:
    """Tests for validate_namespace function."""

    def test_valid_namespace_no_error(self) -> None:
        """Test valid namespace doesn't raise."""
        # Should not raise
        utils.validate_namespace("inception")
        utils.validate_namespace("patterns")

    def test_invalid_namespace_raises(self) -> None:
        """Test invalid namespace raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            utils.validate_namespace("invalid")
        assert "Invalid namespace" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_error_message_lists_valid(self) -> None:
        """Test error message lists valid namespaces."""
        with pytest.raises(ValueError) as exc_info:
            utils.validate_namespace("bad")
        error_msg = str(exc_info.value)
        # Should list at least some valid namespaces
        assert "inception" in error_msg or "Must be one of" in error_msg


# =============================================================================
# Content Size Validation Tests
# =============================================================================


class TestValidateContentSize:
    """Tests for validate_content_size function."""

    def test_small_content_valid(self) -> None:
        """Test small content doesn't raise."""
        utils.validate_content_size("Hello, world!")

    def test_max_size_content_valid(self) -> None:
        """Test content at exactly max size doesn't raise."""
        content = "x" * config.MAX_CONTENT_BYTES
        utils.validate_content_size(content)

    def test_oversized_content_raises(self) -> None:
        """Test content exceeding max raises ValueError."""
        content = "x" * (config.MAX_CONTENT_BYTES + 1)
        with pytest.raises(ValueError) as exc_info:
            utils.validate_content_size(content)
        assert "exceeds maximum" in str(exc_info.value)

    def test_bytes_content_valid(self) -> None:
        """Test bytes content validation works."""
        content = b"Hello, world!"
        utils.validate_content_size(content)

    def test_bytes_oversized_raises(self) -> None:
        """Test oversized bytes raises ValueError."""
        content = b"x" * (config.MAX_CONTENT_BYTES + 1)
        with pytest.raises(ValueError) as exc_info:
            utils.validate_content_size(content)
        assert "exceeds maximum" in str(exc_info.value)

    def test_unicode_content_byte_counting(self) -> None:
        """Test that unicode content is counted by bytes, not chars."""
        # Each emoji is 4 bytes in UTF-8
        emoji = "🔥"
        assert len(emoji) == 1  # One character
        assert len(emoji.encode("utf-8")) == 4  # Four bytes

        # Create content that's under char limit but near byte limit
        content = emoji * (config.MAX_CONTENT_BYTES // 4)
        utils.validate_content_size(content)  # Should not raise

    def test_empty_content_valid(self) -> None:
        """Test empty content doesn't raise."""
        utils.validate_content_size("")
        utils.validate_content_size(b"")


class TestValidateSummaryLength:
    """Tests for validate_summary_length function."""

    def test_short_summary_valid(self) -> None:
        """Test short summary doesn't raise."""
        utils.validate_summary_length("Brief summary")

    def test_max_length_summary_valid(self) -> None:
        """Test summary at exactly max length doesn't raise."""
        summary = "x" * config.MAX_SUMMARY_CHARS
        utils.validate_summary_length(summary)

    def test_oversized_summary_raises(self) -> None:
        """Test summary exceeding max raises ValueError."""
        summary = "x" * (config.MAX_SUMMARY_CHARS + 1)
        with pytest.raises(ValueError) as exc_info:
            utils.validate_summary_length(summary)
        assert "exceeds maximum" in str(exc_info.value)

    def test_empty_summary_valid(self) -> None:
        """Test empty summary doesn't raise."""
        utils.validate_summary_length("")


# =============================================================================
# Git Ref Validation Tests
# =============================================================================


class TestIsValidGitRef:
    """Tests for is_valid_git_ref function."""

    def test_simple_ref_valid(self) -> None:
        """Test simple ref names are valid."""
        assert utils.is_valid_git_ref("main") is True
        assert utils.is_valid_git_ref("develop") is True
        assert utils.is_valid_git_ref("feature-branch") is True

    def test_ref_with_slash_valid(self) -> None:
        """Test refs with slashes are valid."""
        assert utils.is_valid_git_ref("refs/heads/main") is True
        assert utils.is_valid_git_ref("refs/notes/mem") is True
        assert utils.is_valid_git_ref("feature/new-feature") is True

    def test_ref_with_underscore_valid(self) -> None:
        """Test refs with underscores are valid."""
        assert utils.is_valid_git_ref("feature_branch") is True
        assert utils.is_valid_git_ref("my_feature_123") is True

    def test_ref_with_dot_valid(self) -> None:
        """Test refs with dots in middle are valid."""
        assert utils.is_valid_git_ref("v1.0.0") is True
        assert utils.is_valid_git_ref("release.1.0") is True

    def test_empty_ref_invalid(self) -> None:
        """Test empty ref is invalid."""
        assert utils.is_valid_git_ref("") is False

    def test_path_traversal_invalid(self) -> None:
        """Test path traversal sequences are invalid."""
        assert utils.is_valid_git_ref("../evil") is False
        assert utils.is_valid_git_ref("foo/../bar") is False
        assert utils.is_valid_git_ref("..") is False

    def test_double_slash_invalid(self) -> None:
        """Test double slashes are invalid."""
        assert utils.is_valid_git_ref("refs//heads") is False

    def test_shell_metacharacters_invalid(self) -> None:
        """Test shell metacharacters are invalid."""
        assert utils.is_valid_git_ref("ref;rm -rf /") is False
        assert utils.is_valid_git_ref("ref*") is False
        assert utils.is_valid_git_ref("ref?") is False
        assert utils.is_valid_git_ref("ref[0]") is False
        assert utils.is_valid_git_ref("ref\\n") is False

    def test_space_invalid(self) -> None:
        """Test spaces are invalid."""
        assert utils.is_valid_git_ref("ref with space") is False

    def test_leading_dot_invalid(self) -> None:
        """Test leading dot is invalid."""
        assert utils.is_valid_git_ref(".hidden") is False

    def test_trailing_dot_invalid(self) -> None:
        """Test trailing dot is invalid."""
        assert utils.is_valid_git_ref("ref.") is False

    def test_leading_slash_invalid(self) -> None:
        """Test leading slash is invalid."""
        assert utils.is_valid_git_ref("/refs/heads/main") is False

    def test_trailing_slash_invalid(self) -> None:
        """Test trailing slash is invalid."""
        assert utils.is_valid_git_ref("refs/heads/main/") is False

    def test_lock_suffix_invalid(self) -> None:
        """Test .lock suffix is invalid."""
        assert utils.is_valid_git_ref("HEAD.lock") is False
        assert utils.is_valid_git_ref("refs/heads/main.lock") is False

    def test_reflog_syntax_invalid(self) -> None:
        """Test reflog syntax is invalid."""
        assert utils.is_valid_git_ref("HEAD@{0}") is False
        assert utils.is_valid_git_ref("main@{yesterday}") is False

    def test_colon_invalid(self) -> None:
        """Test colon is invalid."""
        assert utils.is_valid_git_ref("HEAD:file") is False

    def test_tilde_invalid(self) -> None:
        """Test tilde (ancestor reference) is invalid."""
        assert utils.is_valid_git_ref("HEAD~1") is False

    def test_caret_invalid(self) -> None:
        """Test caret (parent reference) is invalid."""
        assert utils.is_valid_git_ref("HEAD^") is False


class TestValidateGitRef:
    """Tests for validate_git_ref function."""

    def test_valid_ref_no_error(self) -> None:
        """Test valid ref doesn't raise."""
        utils.validate_git_ref("refs/heads/main")
        utils.validate_git_ref("refs/notes/mem")
        utils.validate_git_ref("feature-branch")

    def test_invalid_ref_raises(self) -> None:
        """Test invalid ref raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            utils.validate_git_ref("../evil")
        assert "Invalid git ref" in str(exc_info.value)

    def test_shell_metachar_raises(self) -> None:
        """Test shell metacharacters raise ValueError."""
        with pytest.raises(ValueError):
            utils.validate_git_ref("ref;echo pwned")


# =============================================================================
# Module Export Tests
# =============================================================================


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_exist(self) -> None:
        """Test all items in __all__ are actually defined."""
        for name in utils.__all__:
            assert hasattr(utils, name), f"'{name}' in __all__ but not defined"

    def test_temporal_functions_exported(self) -> None:
        """Test temporal decay functions are exported."""
        assert "calculate_temporal_decay" in utils.__all__
        assert "calculate_age_days" in utils.__all__

    def test_timestamp_functions_exported(self) -> None:
        """Test timestamp parsing functions are exported."""
        assert "parse_iso_timestamp" in utils.__all__
        assert "parse_iso_timestamp_safe" in utils.__all__

    def test_validation_functions_exported(self) -> None:
        """Test validation functions are exported."""
        assert "validate_namespace" in utils.__all__
        assert "validate_content_size" in utils.__all__
        assert "validate_summary_length" in utils.__all__
        assert "validate_git_ref" in utils.__all__
        assert "is_valid_namespace" in utils.__all__
        assert "is_valid_git_ref" in utils.__all__
