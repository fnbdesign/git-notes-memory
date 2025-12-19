"""Tests for the LifecycleManager module.

Tests cover:
- Constants and configuration
- MemoryStatus enum and transitions
- LifecycleStats tracking
- Content compression/decompression
- LifecycleManager relevance calculations
- Manual state transitions
- Automatic lifecycle processing
- Batch operations
- Query operations
- Singleton behavior
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from git_notes_memory.lifecycle import (
    ARCHIVE_AGE_DAYS,
    ARCHIVED_CONTENT_PREFIX,
    COMPRESSION_LEVEL,
    GARBAGE_COLLECTION_AGE_DAYS,
    MIN_RELEVANCE_FOR_ACTIVE,
    TOMBSTONE_AGE_DAYS,
    TOMBSTONE_SUMMARY,
    LifecycleManager,
    LifecycleStats,
    MemoryStatus,
    compress_content,
    decompress_content,
    get_compression_ratio,
    get_default_manager,
)
from git_notes_memory.models import Memory

if TYPE_CHECKING:
    pass


# =============================================================================
# Helper Functions
# =============================================================================


def _make_memory(
    memory_id: str = "test:abc123:0",
    commit_sha: str = "abc123",
    namespace: str = "decisions",
    summary: str = "Test memory summary",
    content: str = "Test memory content",
    timestamp: datetime | None = None,
    status: str = "active",
    spec: str | None = None,
    tags: tuple[str, ...] = (),
) -> Memory:
    """Create a test Memory with defaults."""
    if timestamp is None:
        timestamp = datetime.now(UTC)

    return Memory(
        id=memory_id,
        commit_sha=commit_sha,
        namespace=namespace,
        summary=summary,
        content=content,
        timestamp=timestamp,
        status=status,
        spec=spec,
        tags=tags,
    )


def _make_old_memory(days_old: float, **kwargs) -> Memory:
    """Create a memory that is a specific number of days old."""
    timestamp = datetime.now(UTC) - timedelta(days=days_old)
    return _make_memory(timestamp=timestamp, **kwargs)


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_archive_age_days(self) -> None:
        """Archive age should be reasonable."""
        assert ARCHIVE_AGE_DAYS > 0
        assert ARCHIVE_AGE_DAYS == 90

    def test_tombstone_age_days(self) -> None:
        """Tombstone age should be greater than archive age."""
        assert TOMBSTONE_AGE_DAYS > ARCHIVE_AGE_DAYS
        assert TOMBSTONE_AGE_DAYS == 180

    def test_garbage_collection_age_days(self) -> None:
        """GC age should be greatest."""
        assert GARBAGE_COLLECTION_AGE_DAYS > TOMBSTONE_AGE_DAYS
        assert GARBAGE_COLLECTION_AGE_DAYS == 365

    def test_min_relevance_for_active(self) -> None:
        """Min relevance should be a reasonable threshold."""
        assert 0 < MIN_RELEVANCE_FOR_ACTIVE < 1
        assert MIN_RELEVANCE_FOR_ACTIVE == 0.1

    def test_compression_level(self) -> None:
        """Compression level should be valid zlib level."""
        assert 1 <= COMPRESSION_LEVEL <= 9

    def test_archived_content_prefix(self) -> None:
        """Archived prefix should be identifiable."""
        assert ARCHIVED_CONTENT_PREFIX.startswith("[ARCHIVED]")

    def test_tombstone_summary(self) -> None:
        """Tombstone summary should be identifiable."""
        assert TOMBSTONE_SUMMARY == "[DELETED]"


# =============================================================================
# Test MemoryStatus Enum
# =============================================================================


class TestMemoryStatus:
    """Tests for the MemoryStatus enum."""

    def test_all_status_values(self) -> None:
        """All expected statuses should exist."""
        assert MemoryStatus.ACTIVE.value == "active"
        assert MemoryStatus.RESOLVED.value == "resolved"
        assert MemoryStatus.ARCHIVED.value == "archived"
        assert MemoryStatus.TOMBSTONE.value == "tombstone"

    def test_active_can_transition_to_resolved(self) -> None:
        """Active can transition to resolved."""
        assert MemoryStatus.ACTIVE.can_transition_to(MemoryStatus.RESOLVED)

    def test_active_can_transition_to_archived(self) -> None:
        """Active can transition to archived."""
        assert MemoryStatus.ACTIVE.can_transition_to(MemoryStatus.ARCHIVED)

    def test_active_can_transition_to_tombstone(self) -> None:
        """Active can transition to tombstone."""
        assert MemoryStatus.ACTIVE.can_transition_to(MemoryStatus.TOMBSTONE)

    def test_active_cannot_transition_to_active(self) -> None:
        """Active cannot transition to itself."""
        assert not MemoryStatus.ACTIVE.can_transition_to(MemoryStatus.ACTIVE)

    def test_resolved_can_transition_to_archived(self) -> None:
        """Resolved can transition to archived."""
        assert MemoryStatus.RESOLVED.can_transition_to(MemoryStatus.ARCHIVED)

    def test_resolved_cannot_transition_to_active(self) -> None:
        """Resolved cannot go back to active."""
        assert not MemoryStatus.RESOLVED.can_transition_to(MemoryStatus.ACTIVE)

    def test_archived_can_transition_to_tombstone(self) -> None:
        """Archived can transition to tombstone."""
        assert MemoryStatus.ARCHIVED.can_transition_to(MemoryStatus.TOMBSTONE)

    def test_archived_can_restore_to_active(self) -> None:
        """Archived can be restored to active."""
        assert MemoryStatus.ARCHIVED.can_transition_to(MemoryStatus.ACTIVE)

    def test_tombstone_can_restore_to_active(self) -> None:
        """Tombstone can be restored to active."""
        assert MemoryStatus.TOMBSTONE.can_transition_to(MemoryStatus.ACTIVE)

    def test_tombstone_cannot_transition_elsewhere(self) -> None:
        """Tombstone cannot go to resolved or archived."""
        assert not MemoryStatus.TOMBSTONE.can_transition_to(MemoryStatus.RESOLVED)
        assert not MemoryStatus.TOMBSTONE.can_transition_to(MemoryStatus.ARCHIVED)


# =============================================================================
# Test LifecycleStats
# =============================================================================


class TestLifecycleStats:
    """Tests for the LifecycleStats class."""

    def test_initial_values(self) -> None:
        """Stats should start at zero."""
        stats = LifecycleStats()
        assert stats.scanned == 0
        assert stats.archived == 0
        assert stats.tombstoned == 0
        assert stats.deleted == 0
        assert stats.errors == 0
        assert stats.skipped == 0

    def test_processed_property(self) -> None:
        """Processed should be sum of modifications."""
        stats = LifecycleStats()
        stats.archived = 5
        stats.tombstoned = 3
        stats.deleted = 2
        assert stats.processed == 10

    def test_repr(self) -> None:
        """Repr should include all fields."""
        stats = LifecycleStats()
        stats.scanned = 100
        stats.archived = 10
        repr_str = repr(stats)
        assert "scanned=100" in repr_str
        assert "archived=10" in repr_str


# =============================================================================
# Test Content Compression
# =============================================================================


class TestContentCompression:
    """Tests for content compression functions."""

    def test_compress_and_decompress_roundtrip(self) -> None:
        """Compress then decompress should return original."""
        original = "This is some test content that should compress well."
        compressed = compress_content(original)
        decompressed = decompress_content(compressed)
        assert decompressed == original

    def test_compression_reduces_size(self) -> None:
        """Compression should reduce size for repetitive content."""
        original = "Hello world! " * 100
        compressed = compress_content(original)
        assert len(compressed) < len(original.encode("utf-8"))

    def test_compression_ratio_calculation(self) -> None:
        """Compression ratio should be correct."""
        original = "Hello world! " * 100
        compressed = compress_content(original)
        ratio = get_compression_ratio(original, compressed)
        assert 0 < ratio < 1  # Should be well compressed

    def test_compression_ratio_empty_string(self) -> None:
        """Empty string should have ratio 1.0."""
        ratio = get_compression_ratio("", b"")
        assert ratio == 1.0

    def test_decompress_invalid_data(self) -> None:
        """Invalid data should raise ValueError."""
        with pytest.raises(ValueError, match="Failed to decompress"):
            decompress_content(b"not valid compressed data")

    def test_compress_unicode_content(self) -> None:
        """Unicode content should compress and decompress correctly."""
        original = "Hello \u4e16\u754c! \U0001f600 \u00e9\u00e0\u00fc"
        compressed = compress_content(original)
        decompressed = decompress_content(compressed)
        assert decompressed == original


# =============================================================================
# Test LifecycleManager Initialization
# =============================================================================


class TestLifecycleManagerInit:
    """Tests for LifecycleManager initialization."""

    def test_default_init(self) -> None:
        """Manager should initialize with defaults."""
        manager = LifecycleManager()
        assert manager.archive_age_days == ARCHIVE_AGE_DAYS
        assert manager.tombstone_age_days == TOMBSTONE_AGE_DAYS
        assert manager.gc_age_days == GARBAGE_COLLECTION_AGE_DAYS
        assert manager.min_relevance == MIN_RELEVANCE_FOR_ACTIVE

    def test_custom_thresholds(self) -> None:
        """Manager should accept custom thresholds."""
        manager = LifecycleManager(
            archive_age_days=30,
            tombstone_age_days=60,
            gc_age_days=90,
            min_relevance=0.2,
        )
        assert manager.archive_age_days == 30
        assert manager.tombstone_age_days == 60
        assert manager.gc_age_days == 90
        assert manager.min_relevance == 0.2

    def test_index_service_not_configured(self) -> None:
        """Accessing index_service without configuration should raise."""
        manager = LifecycleManager()
        with pytest.raises(RuntimeError, match="IndexService not configured"):
            _ = manager.index_service

    def test_set_index_service(self) -> None:
        """Should be able to set index service."""
        manager = LifecycleManager()
        mock_service = MagicMock()
        manager.set_index_service(mock_service)
        assert manager.index_service is mock_service


# =============================================================================
# Test Relevance Calculation
# =============================================================================


class TestRelevanceCalculation:
    """Tests for relevance and age calculations."""

    def test_calculate_relevance_new_memory(self) -> None:
        """New memory should have high relevance."""
        manager = LifecycleManager()
        memory = _make_memory()  # Created now
        relevance = manager.calculate_relevance(memory)
        assert relevance > 0.9  # Very recent

    def test_calculate_relevance_old_memory(self) -> None:
        """Old memory should have low relevance."""
        manager = LifecycleManager()
        memory = _make_old_memory(days_old=90)
        relevance = manager.calculate_relevance(memory)
        assert relevance < 0.2  # Decayed significantly

    def test_calculate_relevance_half_life(self) -> None:
        """Memory at half-life should have ~0.5 relevance."""
        manager = LifecycleManager(half_life_days=30)
        memory = _make_old_memory(days_old=30)
        relevance = manager.calculate_relevance(memory)
        assert 0.4 < relevance < 0.6  # Around 0.5

    def test_get_age_days_new_memory(self) -> None:
        """New memory should have age near 0."""
        manager = LifecycleManager()
        memory = _make_memory()
        age = manager.get_age_days(memory)
        assert age < 0.01  # Less than ~15 minutes

    def test_get_age_days_old_memory(self) -> None:
        """Old memory should have correct age."""
        manager = LifecycleManager()
        memory = _make_old_memory(days_old=45)
        age = manager.get_age_days(memory)
        assert 44.9 < age < 45.1  # Allow small variance


# =============================================================================
# Test Should-Transition Checks
# =============================================================================


class TestShouldTransitionChecks:
    """Tests for should_archive, should_tombstone, should_garbage_collect."""

    def test_should_archive_old_active_memory(self) -> None:
        """Old active memory should be archived."""
        manager = LifecycleManager(archive_age_days=30)
        memory = _make_old_memory(days_old=60, status="active")
        assert manager.should_archive(memory)

    def test_should_not_archive_recent_memory(self) -> None:
        """Recent memory should not be archived."""
        manager = LifecycleManager(archive_age_days=30)
        memory = _make_old_memory(days_old=10, status="active")
        assert not manager.should_archive(memory)

    def test_should_archive_low_relevance_memory(self) -> None:
        """Memory with low relevance should be archived."""
        manager = LifecycleManager(min_relevance=0.5, archive_age_days=365)
        # Create memory old enough to have relevance < 0.5
        memory = _make_old_memory(days_old=31, status="active")  # ~0.5 relevance
        # This might or might not trigger depending on exact timing
        # Let's use a much older memory to be sure
        old_memory = _make_old_memory(days_old=120, status="active")
        assert manager.should_archive(old_memory)

    def test_should_not_archive_already_archived(self) -> None:
        """Already archived memory should not be re-archived."""
        manager = LifecycleManager(archive_age_days=30)
        memory = _make_old_memory(days_old=60, status="archived")
        assert not manager.should_archive(memory)

    def test_should_tombstone_old_archived_memory(self) -> None:
        """Old archived memory should be tombstoned."""
        manager = LifecycleManager(tombstone_age_days=180)
        memory = _make_old_memory(days_old=200, status="archived")
        assert manager.should_tombstone(memory)

    def test_should_not_tombstone_recent_archived(self) -> None:
        """Recent archived memory should not be tombstoned."""
        manager = LifecycleManager(tombstone_age_days=180)
        memory = _make_old_memory(days_old=100, status="archived")
        assert not manager.should_tombstone(memory)

    def test_should_not_tombstone_active_memory(self) -> None:
        """Active memory should not be tombstoned directly."""
        manager = LifecycleManager(tombstone_age_days=180)
        memory = _make_old_memory(days_old=200, status="active")
        assert not manager.should_tombstone(memory)

    def test_should_garbage_collect_old_tombstone(self) -> None:
        """Old tombstone should be garbage collected."""
        manager = LifecycleManager(gc_age_days=365)
        memory = _make_old_memory(days_old=400, status="tombstone")
        assert manager.should_garbage_collect(memory)

    def test_should_not_garbage_collect_recent_tombstone(self) -> None:
        """Recent tombstone should not be garbage collected."""
        manager = LifecycleManager(gc_age_days=365)
        memory = _make_old_memory(days_old=200, status="tombstone")
        assert not manager.should_garbage_collect(memory)


# =============================================================================
# Test Manual Transitions
# =============================================================================


class TestManualTransitions:
    """Tests for manual state transition methods."""

    def test_resolve_active_memory(self) -> None:
        """Should be able to resolve an active memory."""
        mock_index = MagicMock()
        mock_index.get.return_value = _make_memory(status="active")
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.resolve("test:abc123:0")

        assert result is True
        mock_index.update.assert_called_once()
        # Check the updated memory has resolved status
        updated_memory = mock_index.update.call_args[0][0]
        assert updated_memory.status == "resolved"

    def test_resolve_nonexistent_memory(self) -> None:
        """Resolving nonexistent memory should return False."""
        mock_index = MagicMock()
        mock_index.get.return_value = None

        manager = LifecycleManager(index_service=mock_index)
        result = manager.resolve("nonexistent:id:0")

        assert result is False

    def test_archive_memory(self) -> None:
        """Should be able to archive an active memory."""
        mock_index = MagicMock()
        mock_index.get.return_value = _make_memory(
            status="active", content="Original content"
        )
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.archive("test:abc123:0")

        assert result is True
        updated_memory = mock_index.update.call_args[0][0]
        assert updated_memory.status == "archived"
        assert updated_memory.content.startswith(ARCHIVED_CONTENT_PREFIX)

    def test_archive_without_compression(self) -> None:
        """Archive without compression should preserve content."""
        mock_index = MagicMock()
        original_content = "Original content"
        mock_index.get.return_value = _make_memory(
            status="active", content=original_content
        )
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.archive("test:abc123:0", compress=False)

        assert result is True
        updated_memory = mock_index.update.call_args[0][0]
        # Without compression, content is unchanged
        assert updated_memory.content == original_content

    def test_delete_memory_soft(self) -> None:
        """Delete should tombstone, not hard delete."""
        mock_index = MagicMock()
        mock_index.get.return_value = _make_memory(status="active")
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.delete("test:abc123:0")

        assert result is True
        updated_memory = mock_index.update.call_args[0][0]
        assert updated_memory.status == "tombstone"
        assert updated_memory.summary == TOMBSTONE_SUMMARY
        assert updated_memory.content == ""

    def test_restore_archived_memory(self) -> None:
        """Should be able to restore an archived memory."""
        mock_index = MagicMock()
        mock_index.get.return_value = _make_memory(status="archived")
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.restore("test:abc123:0")

        assert result is True
        updated_memory = mock_index.update.call_args[0][0]
        assert updated_memory.status == "active"

    def test_restore_tombstoned_memory(self) -> None:
        """Should be able to restore a tombstoned memory."""
        mock_index = MagicMock()
        mock_index.get.return_value = _make_memory(status="tombstone")
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.restore("test:abc123:0")

        assert result is True
        updated_memory = mock_index.update.call_args[0][0]
        assert updated_memory.status == "active"

    def test_hard_delete(self) -> None:
        """Hard delete should call index.delete."""
        mock_index = MagicMock()
        mock_index.delete.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.hard_delete("test:abc123:0")

        assert result is True
        mock_index.delete.assert_called_once_with("test:abc123:0")

    def test_invalid_transition(self) -> None:
        """Invalid transition should return False."""
        mock_index = MagicMock()
        # Resolved cannot go back to active via resolve
        mock_index.get.return_value = _make_memory(status="resolved")

        manager = LifecycleManager(index_service=mock_index)
        # Trying to resolve an already resolved memory (resolved -> resolved)
        # This should fail because resolved cannot transition to itself
        # Actually, let's try resolved -> active which is invalid
        result = manager._transition("test:abc123:0", MemoryStatus.ACTIVE)

        assert result is False


# =============================================================================
# Test Batch Operations
# =============================================================================


class TestBatchOperations:
    """Tests for batch operations."""

    def test_process_lifecycle_archives_old_memories(self) -> None:
        """Process lifecycle should archive old active memories."""
        mock_index = MagicMock()

        # Create a mix of memories
        old_active = _make_old_memory(days_old=100, memory_id="old:active:0")
        recent_active = _make_memory(memory_id="recent:active:0")
        mock_index.get_all_ids.return_value = ["old:active:0", "recent:active:0"]
        mock_index.get_batch.return_value = [old_active, recent_active]
        mock_index.get.side_effect = lambda id: (
            old_active if id == "old:active:0" else recent_active
        )
        mock_index.update.return_value = True

        manager = LifecycleManager(
            index_service=mock_index, archive_age_days=90, min_relevance=0.05
        )
        stats = manager.process_lifecycle()

        assert stats.scanned == 2
        assert stats.archived == 1
        assert stats.skipped == 1

    def test_process_lifecycle_dry_run(self) -> None:
        """Dry run should not modify anything."""
        mock_index = MagicMock()
        old_active = _make_old_memory(days_old=100, memory_id="old:active:0")
        mock_index.get_all_ids.return_value = ["old:active:0"]
        mock_index.get_batch.return_value = [old_active]

        manager = LifecycleManager(index_service=mock_index, archive_age_days=90)
        stats = manager.process_lifecycle(dry_run=True)

        assert stats.archived == 1
        mock_index.update.assert_not_called()

    def test_archive_batch(self) -> None:
        """Archive batch should archive multiple memories."""
        mock_index = MagicMock()
        memories = [_make_memory(memory_id=f"test:id:{i}") for i in range(3)]
        mock_index.get.side_effect = lambda id: next(
            (m for m in memories if m.id == id), None
        )
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        stats = manager.archive_batch([m.id for m in memories])

        assert stats.scanned == 3
        assert stats.archived == 3
        assert mock_index.update.call_count == 3

    def test_garbage_collect(self) -> None:
        """Garbage collect should delete old tombstones."""
        mock_index = MagicMock()
        old_tombstone = _make_old_memory(
            days_old=400, status="tombstone", memory_id="old:ts:0"
        )
        recent_tombstone = _make_old_memory(
            days_old=200, status="tombstone", memory_id="recent:ts:0"
        )
        mock_index.get_all_ids.return_value = ["old:ts:0", "recent:ts:0"]
        mock_index.get_batch.return_value = [old_tombstone, recent_tombstone]
        mock_index.delete.return_value = True

        manager = LifecycleManager(index_service=mock_index, gc_age_days=365)
        stats = manager.garbage_collect()

        assert stats.scanned == 2
        assert stats.deleted == 1
        assert stats.skipped == 1


# =============================================================================
# Test Query Operations
# =============================================================================


class TestQueryOperations:
    """Tests for query operations."""

    def test_get_stale_memories(self) -> None:
        """Should return memories below relevance threshold."""
        mock_index = MagicMock()
        stale = _make_old_memory(days_old=120, memory_id="stale:0", status="active")
        fresh = _make_memory(memory_id="fresh:0", status="active")
        mock_index.get_all_ids.return_value = ["stale:0", "fresh:0"]
        mock_index.get_batch.return_value = [stale, fresh]

        manager = LifecycleManager(index_service=mock_index)
        result = manager.get_stale_memories(max_relevance=0.5)

        assert len(result) == 1
        assert result[0].id == "stale:0"

    def test_get_stale_memories_with_min_age(self) -> None:
        """Should filter by minimum age."""
        mock_index = MagicMock()
        old_stale = _make_old_memory(days_old=120, memory_id="old:0", status="active")
        young_stale = _make_old_memory(
            days_old=40, memory_id="young:0", status="active"
        )
        mock_index.get_all_ids.return_value = ["old:0", "young:0"]
        mock_index.get_batch.return_value = [old_stale, young_stale]

        manager = LifecycleManager(index_service=mock_index)
        result = manager.get_stale_memories(max_relevance=1.0, min_age_days=60)

        assert len(result) == 1
        assert result[0].id == "old:0"

    def test_get_lifecycle_summary(self) -> None:
        """Should return counts by status."""
        mock_index = MagicMock()
        memories = [
            _make_memory(status="active", memory_id="a:0"),
            _make_memory(status="active", memory_id="a:1"),
            _make_memory(status="resolved", memory_id="r:0"),
            _make_memory(status="archived", memory_id="ar:0"),
        ]
        mock_index.get_all_ids.return_value = [m.id for m in memories]
        mock_index.get_batch.return_value = memories

        manager = LifecycleManager(index_service=mock_index)
        summary = manager.get_lifecycle_summary()

        assert summary["active"] == 2
        assert summary["resolved"] == 1
        assert summary["archived"] == 1
        assert summary["tombstone"] == 0
        assert summary["total"] == 4


# =============================================================================
# Test Singleton
# =============================================================================


class TestSingleton:
    """Tests for singleton behavior."""

    def test_get_default_manager_creates_instance(self) -> None:
        """Should create manager on first call."""
        from git_notes_memory import lifecycle

        lifecycle._manager = None

        manager = get_default_manager()
        assert manager is not None
        assert isinstance(manager, LifecycleManager)

    def test_get_default_manager_returns_same_instance(self) -> None:
        """Should return same instance on subsequent calls."""
        from git_notes_memory import lifecycle

        lifecycle._manager = None

        manager1 = get_default_manager()
        manager2 = get_default_manager()
        assert manager1 is manager2

    def test_get_default_manager_with_index_service(self) -> None:
        """Should set index service on manager."""
        from git_notes_memory import lifecycle

        lifecycle._manager = None

        mock_index = MagicMock()
        manager = get_default_manager(index_service=mock_index)
        assert manager.index_service is mock_index

    def test_singleton_reset_works(self) -> None:
        """Reset should clear singleton."""
        from git_notes_memory import lifecycle

        manager1 = get_default_manager()
        lifecycle._manager = None
        manager2 = get_default_manager()

        assert manager1 is not manager2


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_transition_handles_exception(self) -> None:
        """Transition should handle exceptions gracefully."""
        mock_index = MagicMock()
        mock_index.get.side_effect = Exception("Database error")

        manager = LifecycleManager(index_service=mock_index)
        result = manager.resolve("test:id:0")

        assert result is False

    def test_process_lifecycle_handles_retrieval_error(self) -> None:
        """Process lifecycle should handle retrieval errors."""
        mock_index = MagicMock()
        mock_index.get_all_ids.side_effect = Exception("Database error")

        manager = LifecycleManager(index_service=mock_index)
        stats = manager.process_lifecycle()

        assert stats.errors == 1

    def test_archive_already_archived_content(self) -> None:
        """Archiving already archived content should not double-compress."""
        mock_index = MagicMock()
        already_archived = _make_memory(
            status="active",  # Status is active but content has prefix
            content=f"{ARCHIVED_CONTENT_PREFIX}already compressed",
        )
        mock_index.get.return_value = already_archived
        mock_index.update.return_value = True

        manager = LifecycleManager(index_service=mock_index)
        result = manager.archive("test:id:0")

        assert result is True
        updated = mock_index.update.call_args[0][0]
        # Content should not be double-prefixed
        assert not updated.content.startswith(
            f"{ARCHIVED_CONTENT_PREFIX}{ARCHIVED_CONTENT_PREFIX}"
        )

    def test_hard_delete_handles_exception(self) -> None:
        """Hard delete should handle exceptions."""
        mock_index = MagicMock()
        mock_index.delete.side_effect = Exception("Database error")

        manager = LifecycleManager(index_service=mock_index)
        result = manager.hard_delete("test:id:0")

        assert result is False

    def test_get_lifecycle_summary_handles_error(self) -> None:
        """Summary should handle errors gracefully."""
        mock_index = MagicMock()
        mock_index.get_all_ids.side_effect = Exception("Database error")

        manager = LifecycleManager(index_service=mock_index)
        summary = manager.get_lifecycle_summary()

        # Should return default empty summary
        assert summary["total"] == 0

    def test_get_stale_memories_handles_error(self) -> None:
        """Get stale should handle errors gracefully."""
        mock_index = MagicMock()
        mock_index.get_all_ids.side_effect = Exception("Database error")

        manager = LifecycleManager(index_service=mock_index)
        result = manager.get_stale_memories()

        assert result == []


# =============================================================================
# Test Filter Functions
# =============================================================================


class TestFiltering:
    """Tests for memory filtering in _get_memories."""

    def test_filter_by_spec(self) -> None:
        """Should filter by spec."""
        mock_index = MagicMock()
        with_spec = _make_memory(spec="project-a", memory_id="a:0")
        without_spec = _make_memory(spec=None, memory_id="b:0")
        other_spec = _make_memory(spec="project-b", memory_id="c:0")
        mock_index.get_all_ids.return_value = ["a:0", "b:0", "c:0"]
        mock_index.get_batch.return_value = [with_spec, without_spec, other_spec]

        manager = LifecycleManager(index_service=mock_index)
        result = manager._get_memories(spec="project-a")

        assert len(result) == 1
        assert result[0].id == "a:0"

    def test_filter_by_namespace(self) -> None:
        """Should filter by namespace."""
        mock_index = MagicMock()
        decisions = _make_memory(namespace="decisions", memory_id="d:0")
        learnings = _make_memory(namespace="learnings", memory_id="l:0")
        mock_index.get_all_ids.return_value = ["d:0", "l:0"]
        mock_index.get_batch.return_value = [decisions, learnings]

        manager = LifecycleManager(index_service=mock_index)
        result = manager._get_memories(namespace="decisions")

        assert len(result) == 1
        assert result[0].id == "d:0"

    def test_filter_by_status(self) -> None:
        """Should filter by status."""
        mock_index = MagicMock()
        active = _make_memory(status="active", memory_id="a:0")
        archived = _make_memory(status="archived", memory_id="ar:0")
        mock_index.get_all_ids.return_value = ["a:0", "ar:0"]
        mock_index.get_batch.return_value = [active, archived]

        manager = LifecycleManager(index_service=mock_index)
        result = manager._get_memories(status=MemoryStatus.ACTIVE)

        assert len(result) == 1
        assert result[0].id == "a:0"

    def test_filter_combined(self) -> None:
        """Should combine multiple filters."""
        mock_index = MagicMock()
        match = _make_memory(
            spec="proj", namespace="decisions", status="active", memory_id="m:0"
        )
        wrong_spec = _make_memory(
            spec="other", namespace="decisions", status="active", memory_id="ws:0"
        )
        wrong_ns = _make_memory(
            spec="proj", namespace="learnings", status="active", memory_id="wn:0"
        )
        mock_index.get_all_ids.return_value = ["m:0", "ws:0", "wn:0"]
        mock_index.get_batch.return_value = [match, wrong_spec, wrong_ns]

        manager = LifecycleManager(index_service=mock_index)
        result = manager._get_memories(spec="proj", namespace="decisions")

        assert len(result) == 1
        assert result[0].id == "m:0"
