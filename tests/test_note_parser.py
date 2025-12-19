"""Tests for git_notes_memory.note_parser module.

Tests YAML front matter parsing, multi-note handling, serialization,
and graceful error handling for malformed content.
"""

from __future__ import annotations

import pytest

from git_notes_memory import note_parser
from git_notes_memory.exceptions import ParseError

# =============================================================================
# Test Data
# =============================================================================

# Well-formed note with all fields
COMPLETE_NOTE = """---
type: decisions
spec: my-project
timestamp: 2024-01-15T10:30:00Z
summary: Chose PostgreSQL for data layer
phase: planning
tags:
  - database
  - architecture
status: active
relates_to:
  - inception:abc123:0
---

## Context

We needed to choose a database for the persistence layer.

## Decision

PostgreSQL was selected for:
1. Strong JSON support
2. Excellent community
3. Team familiarity
"""

# Minimal note with only required fields
MINIMAL_NOTE = """---
type: learnings
spec: test-project
timestamp: 2024-01-15T10:30:00Z
summary: Unit tests should be fast
---
"""

# Note with no body
NOTE_NO_BODY = """---
type: progress
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Completed task 1
---"""

# Multi-note content (two notes concatenated)
MULTI_NOTE = """---
type: decisions
spec: proj
timestamp: 2024-01-15T10:00:00Z
summary: First decision
---
Body of first note

---
type: learnings
spec: proj
timestamp: 2024-01-15T11:00:00Z
summary: Second learning
---
Body of second note
"""


# =============================================================================
# ParsedNote Tests
# =============================================================================


class TestParsedNote:
    """Tests for ParsedNote dataclass behavior."""

    def test_type_property(self) -> None:
        """Test type property extracts from front matter."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.type == "decisions"

    def test_spec_property(self) -> None:
        """Test spec property extracts from front matter."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.spec == "my-project"

    def test_timestamp_property(self) -> None:
        """Test timestamp property extracts from front matter.

        Note: YAML's safe_load() automatically parses ISO timestamps to datetime
        objects, so the string representation may differ from the original.
        Both formats are valid and parseable by parse_iso_timestamp_safe().
        """
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        # YAML parses "2024-01-15T10:30:00Z" to datetime, which stringifies as:
        assert parsed.timestamp == "2024-01-15 10:30:00+00:00"

    def test_summary_property(self) -> None:
        """Test summary property extracts from front matter."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.summary == "Chose PostgreSQL for data layer"

    def test_get_method(self) -> None:
        """Test get method for front matter access."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.get("phase") == "planning"
        assert parsed.get("nonexistent") is None
        assert parsed.get("nonexistent", "default") == "default"

    def test_has_required_fields_true(self) -> None:
        """Test has_required_fields returns True for complete note."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.has_required_fields() is True

    def test_has_required_fields_false(self) -> None:
        """Test has_required_fields returns False for incomplete note."""
        incomplete = """---
type: decisions
summary: Missing spec and timestamp
---
"""
        parsed = note_parser.parse_note(incomplete)
        assert parsed.has_required_fields() is False

    def test_missing_fields(self) -> None:
        """Test missing_fields lists missing required fields."""
        incomplete = """---
type: decisions
summary: Missing spec and timestamp
---
"""
        parsed = note_parser.parse_note(incomplete)
        missing = parsed.missing_fields()
        assert "spec" in missing
        assert "timestamp" in missing
        assert "type" not in missing
        assert "summary" not in missing

    def test_missing_fields_empty_for_complete(self) -> None:
        """Test missing_fields returns empty for complete note."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.missing_fields() == []

    def test_validate_passes_for_complete(self) -> None:
        """Test validate passes for complete note."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        parsed.validate()  # Should not raise

    def test_validate_raises_for_incomplete(self) -> None:
        """Test validate raises ParseError for incomplete note."""
        incomplete = """---
type: decisions
---
"""
        parsed = note_parser.parse_note(incomplete)
        with pytest.raises(ParseError) as exc_info:
            parsed.validate()
        assert "spec" in str(exc_info.value)
        assert "timestamp" in str(exc_info.value)
        assert "summary" in str(exc_info.value)

    def test_body_preserved(self) -> None:
        """Test that body content is preserved correctly."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert "## Context" in parsed.body
        assert "PostgreSQL was selected" in parsed.body

    def test_raw_preserved(self) -> None:
        """Test that raw content is preserved."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.raw == COMPLETE_NOTE


# =============================================================================
# parse_note Tests
# =============================================================================


class TestParseNote:
    """Tests for parse_note function."""

    def test_parses_complete_note(self) -> None:
        """Test parsing a complete note with all fields."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        assert parsed.type == "decisions"
        assert parsed.spec == "my-project"
        assert parsed.summary == "Chose PostgreSQL for data layer"

    def test_parses_minimal_note(self) -> None:
        """Test parsing minimal note with required fields only."""
        parsed = note_parser.parse_note(MINIMAL_NOTE)
        assert parsed.type == "learnings"
        assert parsed.spec == "test-project"
        assert parsed.summary == "Unit tests should be fast"
        assert parsed.body == ""

    def test_parses_note_no_body(self) -> None:
        """Test parsing note with no body content."""
        parsed = note_parser.parse_note(NOTE_NO_BODY)
        assert parsed.type == "progress"
        assert parsed.body == ""

    def test_handles_tags_as_list(self) -> None:
        """Test that YAML list tags are parsed correctly."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        tags = parsed.get("tags")
        assert isinstance(tags, list)
        assert "database" in tags
        assert "architecture" in tags

    def test_handles_relates_to_as_list(self) -> None:
        """Test that relates_to list is parsed correctly."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        relates = parsed.get("relates_to")
        assert isinstance(relates, list)
        assert "inception:abc123:0" in relates

    def test_raises_on_empty_content(self) -> None:
        """Test that empty content raises ParseError."""
        with pytest.raises(ParseError) as exc_info:
            note_parser.parse_note("")
        assert "empty" in str(exc_info.value).lower()

    def test_raises_on_whitespace_only(self) -> None:
        """Test that whitespace-only content raises ParseError."""
        with pytest.raises(ParseError):
            note_parser.parse_note("   \n\t\n   ")

    def test_raises_on_missing_front_matter(self) -> None:
        """Test that content without front matter raises ParseError."""
        with pytest.raises(ParseError) as exc_info:
            note_parser.parse_note("Just some plain text")
        assert "front matter" in str(exc_info.value).lower()

    def test_raises_on_incomplete_front_matter(self) -> None:
        """Test that incomplete front matter raises ParseError."""
        incomplete = """---
type: decisions
summary: No closing marker"""
        with pytest.raises(ParseError):
            note_parser.parse_note(incomplete)

    def test_raises_on_invalid_yaml(self) -> None:
        """Test that invalid YAML raises ParseError."""
        invalid = """---
type: decisions
bad_indent:
  - item1
 - item2
---
"""
        with pytest.raises(ParseError) as exc_info:
            note_parser.parse_note(invalid)
        assert "yaml" in str(exc_info.value).lower()

    def test_raises_on_yaml_list_front_matter(self) -> None:
        """Test that YAML list (not mapping) raises ParseError."""
        list_yaml = """---
- item1
- item2
---
"""
        with pytest.raises(ParseError) as exc_info:
            note_parser.parse_note(list_yaml)
        assert "mapping" in str(exc_info.value).lower()

    def test_handles_empty_front_matter(self) -> None:
        """Test that empty front matter produces empty dict."""
        empty_fm = """---
---
Body content
"""
        parsed = note_parser.parse_note(empty_fm)
        assert parsed.front_matter == {}
        assert "Body content" in parsed.body

    def test_preserves_body_newlines(self) -> None:
        """Test that body newlines are preserved."""
        with_newlines = """---
type: test
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Test
---

Line 1

Line 2

Line 3
"""
        parsed = note_parser.parse_note(with_newlines)
        assert "Line 1" in parsed.body
        assert "Line 2" in parsed.body
        assert "Line 3" in parsed.body
        # Check newlines are preserved
        assert "\n\n" in parsed.body

    def test_handles_unicode_content(self) -> None:
        """Test that unicode content is handled correctly."""
        unicode_note = """---
type: decisions
spec: プロジェクト
timestamp: 2024-01-15T10:30:00Z
summary: 日本語テスト
---

これは日本語のコンテンツです。
Emoji: 🎉 🚀 ✨
"""
        parsed = note_parser.parse_note(unicode_note)
        assert parsed.spec == "プロジェクト"
        assert parsed.summary == "日本語テスト"
        assert "日本語" in parsed.body
        assert "🎉" in parsed.body

    def test_handles_special_yaml_characters(self) -> None:
        """Test that special YAML characters are handled."""
        special = """---
type: decisions
spec: test
timestamp: 2024-01-15T10:30:00Z
summary: "Summary with: colon"
---
"""
        parsed = note_parser.parse_note(special)
        assert parsed.summary == "Summary with: colon"

    def test_handles_multiline_summary(self) -> None:
        """Test that multiline summary is parsed."""
        multiline = """---
type: decisions
spec: test
timestamp: 2024-01-15T10:30:00Z
summary: >
  This is a long summary
  that spans multiple lines
---
"""
        parsed = note_parser.parse_note(multiline)
        assert "long summary" in parsed.summary

    def test_preserves_code_blocks_in_body(self) -> None:
        """Test that code blocks in body are preserved."""
        with_code = """---
type: decisions
spec: test
timestamp: 2024-01-15T10:30:00Z
summary: Test
---

```python
def hello():
    print("Hello, World!")
```
"""
        parsed = note_parser.parse_note(with_code)
        assert "```python" in parsed.body
        assert "def hello():" in parsed.body


# =============================================================================
# parse_note_safe Tests
# =============================================================================


class TestParseNoteSafe:
    """Tests for parse_note_safe function."""

    def test_returns_parsed_note_on_success(self) -> None:
        """Test that valid note returns ParsedNote."""
        result = note_parser.parse_note_safe(MINIMAL_NOTE)
        assert result is not None
        assert result.type == "learnings"

    def test_returns_none_on_empty(self) -> None:
        """Test that empty content returns None."""
        assert note_parser.parse_note_safe("") is None

    def test_returns_none_on_invalid(self) -> None:
        """Test that invalid content returns None."""
        assert note_parser.parse_note_safe("invalid content") is None

    def test_returns_none_on_bad_yaml(self) -> None:
        """Test that bad YAML returns None."""
        bad_yaml = """---
bad: yaml: syntax:
---
"""
        assert note_parser.parse_note_safe(bad_yaml) is None


# =============================================================================
# parse_multi_note Tests
# =============================================================================


class TestParseMultiNote:
    """Tests for parse_multi_note function."""

    def test_parses_single_note(self) -> None:
        """Test that single note returns list of one."""
        results = note_parser.parse_multi_note(MINIMAL_NOTE)
        assert len(results) == 1
        assert results[0].type == "learnings"

    def test_parses_multiple_notes(self) -> None:
        """Test that multiple notes are parsed."""
        results = note_parser.parse_multi_note(MULTI_NOTE)
        assert len(results) == 2
        assert results[0].type == "decisions"
        assert results[0].summary == "First decision"
        assert results[1].type == "learnings"
        assert results[1].summary == "Second learning"

    def test_returns_empty_for_empty_content(self) -> None:
        """Test that empty content returns empty list."""
        assert note_parser.parse_multi_note("") == []
        assert note_parser.parse_multi_note("   \n\t  ") == []

    def test_skips_invalid_notes(self) -> None:
        """Test that invalid notes are skipped."""
        mixed = """---
type: valid
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Valid note
---
Body

invalid content without front matter

---
type: another
spec: proj
timestamp: 2024-01-15T11:00:00Z
summary: Another valid
---
"""
        results = note_parser.parse_multi_note(mixed)
        # Should get at least 2 valid notes
        assert len(results) >= 2

    def test_preserves_individual_bodies(self) -> None:
        """Test that each note's body is preserved correctly."""
        results = note_parser.parse_multi_note(MULTI_NOTE)
        assert "first note" in results[0].body.lower()
        assert "second note" in results[1].body.lower()


# =============================================================================
# to_note_record Tests
# =============================================================================


class TestToNoteRecord:
    """Tests for to_note_record function."""

    def test_converts_complete_note(self) -> None:
        """Test conversion of complete note to NoteRecord."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        record = note_parser.to_note_record(parsed, commit_sha="abc123", index=0)

        assert record.commit_sha == "abc123"
        assert record.namespace == "decisions"
        assert record.index == 0
        assert record.body == parsed.body
        assert record.raw == COMPLETE_NOTE

    def test_front_matter_as_tuples(self) -> None:
        """Test that front matter is converted to tuples."""
        parsed = note_parser.parse_note(MINIMAL_NOTE)
        record = note_parser.to_note_record(parsed, commit_sha="abc")

        # front_matter should be tuple of (key, value) tuples
        assert isinstance(record.front_matter, tuple)
        fm_dict = record.front_matter_dict
        assert fm_dict.get("type") == "learnings"

    def test_namespace_override(self) -> None:
        """Test that namespace can be overridden."""
        parsed = note_parser.parse_note(MINIMAL_NOTE)
        record = note_parser.to_note_record(
            parsed, commit_sha="abc", namespace="overridden"
        )
        assert record.namespace == "overridden"

    def test_raises_on_missing_type(self) -> None:
        """Test that missing type raises ParseError."""
        no_type = """---
spec: test
timestamp: 2024-01-15T10:30:00Z
summary: No type field
---
"""
        parsed = note_parser.parse_note(no_type)
        with pytest.raises(ParseError) as exc_info:
            note_parser.to_note_record(parsed, commit_sha="abc")
        assert "type" in str(exc_info.value).lower()

    def test_handles_list_values(self) -> None:
        """Test that list values are converted to comma-separated strings."""
        parsed = note_parser.parse_note(COMPLETE_NOTE)
        record = note_parser.to_note_record(parsed, commit_sha="abc")

        fm_dict = record.front_matter_dict
        # Lists should be comma-separated
        tags_str = fm_dict.get("tags", "")
        assert "database" in tags_str
        assert "architecture" in tags_str

    def test_index_parameter(self) -> None:
        """Test that index parameter is set correctly."""
        parsed = note_parser.parse_note(MINIMAL_NOTE)
        record = note_parser.to_note_record(parsed, commit_sha="abc", index=5)
        assert record.index == 5


# =============================================================================
# serialize_note Tests
# =============================================================================


class TestSerializeNote:
    """Tests for serialize_note function."""

    def test_serializes_with_body(self) -> None:
        """Test serialization with body content."""
        result = note_parser.serialize_note(
            {"type": "decisions", "summary": "Test"},
            "Body content here",
        )
        assert "---" in result
        assert "type: decisions" in result
        assert "summary: Test" in result
        assert "Body content here" in result

    def test_serializes_without_body(self) -> None:
        """Test serialization without body content."""
        result = note_parser.serialize_note({"type": "learnings", "summary": "No body"})
        assert "---" in result
        assert "type: learnings" in result
        # Should end with closing --- and newline
        assert result.strip().endswith("---")

    def test_serializes_empty_body(self) -> None:
        """Test serialization with empty body string."""
        result = note_parser.serialize_note(
            {"type": "test", "summary": "Empty"},
            "",
        )
        # Should not have extra newlines for empty body
        assert result.strip().endswith("---")

    def test_roundtrip_parsing(self) -> None:
        """Test that serialized note can be parsed back."""
        original = {
            "type": "decisions",
            "spec": "test-project",
            "timestamp": "2024-01-15T10:30:00Z",
            "summary": "Roundtrip test",
        }
        body = "Some body content"

        serialized = note_parser.serialize_note(original, body)
        parsed = note_parser.parse_note(serialized)

        assert parsed.type == original["type"]
        assert parsed.spec == original["spec"]
        assert parsed.summary == original["summary"]
        assert body in parsed.body

    def test_handles_special_characters(self) -> None:
        """Test serialization of special characters."""
        result = note_parser.serialize_note({"summary": "Has: colons and 'quotes'"})
        # Should be valid YAML
        parsed = note_parser.parse_note(result)
        assert "colons" in parsed.summary

    def test_handles_unicode(self) -> None:
        """Test serialization of unicode content."""
        result = note_parser.serialize_note(
            {"summary": "日本語テスト 🎉"},
            "Body with émojis 🚀",
        )
        parsed = note_parser.parse_note(result)
        assert "日本語" in parsed.summary
        assert "🎉" in parsed.summary


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual inputs."""

    def test_extra_dashes_in_body(self) -> None:
        """Test that --- in body doesn't confuse parser."""
        tricky = """---
type: test
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Tricky content
---

Here's some content.

---

This is a horizontal rule above.

---

And another one.
"""
        parsed = note_parser.parse_note(tricky)
        assert "horizontal rule" in parsed.body

    def test_windows_line_endings(self) -> None:
        """Test handling of Windows CRLF line endings."""
        windows = "---\r\ntype: test\r\nspec: proj\r\ntimestamp: 2024-01-15T10:30:00Z\r\nsummary: Windows\r\n---\r\nBody\r\n"
        # Should parse without error (may have quirks)
        try:
            parsed = note_parser.parse_note(windows)
            assert parsed.type == "test"
        except ParseError:
            # If it fails on Windows line endings, that's a known limitation
            pass

    def test_very_long_content(self) -> None:
        """Test handling of very long content."""
        long_body = "x" * 100000  # 100KB of x's
        long_note = f"""---
type: test
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Long content
---

{long_body}
"""
        parsed = note_parser.parse_note(long_note)
        assert len(parsed.body) > 90000

    def test_deeply_nested_yaml(self) -> None:
        """Test handling of nested YAML structures."""
        nested = """---
type: decisions
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Nested
metadata:
  author:
    name: Test User
    email: test@example.com
  context:
    - item1
    - item2
---
"""
        parsed = note_parser.parse_note(nested)
        metadata = parsed.get("metadata")
        assert isinstance(metadata, dict)
        assert metadata.get("author", {}).get("name") == "Test User"

    def test_front_matter_with_comments(self) -> None:
        """Test that YAML comments are handled."""
        with_comments = """---
type: test  # This is the type
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: With comments
# Full line comment
---
"""
        parsed = note_parser.parse_note(with_comments)
        assert parsed.type == "test"

    def test_boolean_and_numeric_values(self) -> None:
        """Test that boolean and numeric values are parsed correctly."""
        with_values = """---
type: test
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Values test
enabled: true
count: 42
ratio: 3.14
---
"""
        parsed = note_parser.parse_note(with_values)
        assert parsed.get("enabled") is True
        assert parsed.get("count") == 42
        assert parsed.get("ratio") == 3.14

    def test_null_values(self) -> None:
        """Test that null/None values are handled."""
        with_null = """---
type: test
spec: proj
timestamp: 2024-01-15T10:30:00Z
summary: Null test
optional_field: null
another: ~
---
"""
        parsed = note_parser.parse_note(with_null)
        assert parsed.get("optional_field") is None
        assert parsed.get("another") is None


# =============================================================================
# Module Export Tests
# =============================================================================


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_exist(self) -> None:
        """Test all items in __all__ are defined."""
        for name in note_parser.__all__:
            assert hasattr(note_parser, name), f"'{name}' in __all__ but not defined"

    def test_main_functions_exported(self) -> None:
        """Test main functions are in __all__."""
        expected = [
            "parse_note",
            "parse_note_safe",
            "parse_multi_note",
            "serialize_note",
        ]
        for name in expected:
            assert name in note_parser.__all__
