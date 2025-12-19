"""Lifecycle management for memory aging and archival.

This module provides the LifecycleManager for managing memory lifecycle states
and automatic archival. It handles:

- Memory state transitions: active → resolved → archived → tombstone
- Automatic archival based on age and relevance decay
- Content compression for archived memories
- Garbage collection for tombstoned memories
- Relevance scoring based on temporal decay

The lifecycle follows this flow:
1. Active: Newly captured, fully relevant
2. Resolved: Explicitly marked complete (optional)
3. Archived: Old/decayed, content compressed
4. Tombstone: Marked for deletion, minimal footprint

State transitions can be:
- Manual: User explicitly changes state (resolve, archive, delete)
- Automatic: Based on age thresholds and decay calculations
"""

from __future__ import annotations

import logging
import zlib
from dataclasses import replace
from enum import Enum
from typing import TYPE_CHECKING, Any

from git_notes_memory.config import DECAY_HALF_LIFE_DAYS
from git_notes_memory.utils import calculate_age_days, calculate_temporal_decay

if TYPE_CHECKING:
    from collections.abc import Sequence

    from git_notes_memory.index import IndexService
    from git_notes_memory.models import Memory

__all__ = [
    "LifecycleManager",
    "MemoryStatus",
    "LifecycleStats",
    "get_default_manager",
]

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Age thresholds in days for automatic transitions
ARCHIVE_AGE_DAYS = 90  # Auto-archive after 90 days
TOMBSTONE_AGE_DAYS = 180  # Auto-tombstone after 180 days (from creation)
GARBAGE_COLLECTION_AGE_DAYS = 365  # Delete tombstoned after 1 year

# Relevance threshold for archival (decay factor)
MIN_RELEVANCE_FOR_ACTIVE = 0.1  # Below this, consider for archival

# Content compression settings
COMPRESSION_LEVEL = 6  # zlib compression level (1-9)
ARCHIVED_CONTENT_PREFIX = "[ARCHIVED] "
TOMBSTONE_SUMMARY = "[DELETED]"


class MemoryStatus(str, Enum):
    """Memory lifecycle status.

    Memories progress through these states:
    - ACTIVE: Fully available, not yet resolved
    - RESOLVED: Task completed, but still relevant
    - ARCHIVED: Old memory, content may be compressed
    - TOMBSTONE: Marked for deletion
    """

    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"
    TOMBSTONE = "tombstone"

    def can_transition_to(self, target: MemoryStatus) -> bool:
        """Check if this status can transition to the target status.

        Valid transitions:
        - active → resolved, archived, tombstone
        - resolved → archived, tombstone
        - archived → tombstone, active (restore)
        - tombstone → (none, except manual restore to active)

        Args:
            target: The target status to transition to.

        Returns:
            True if the transition is valid.
        """
        valid_transitions: dict[MemoryStatus, set[MemoryStatus]] = {
            MemoryStatus.ACTIVE: {
                MemoryStatus.RESOLVED,
                MemoryStatus.ARCHIVED,
                MemoryStatus.TOMBSTONE,
            },
            MemoryStatus.RESOLVED: {
                MemoryStatus.ARCHIVED,
                MemoryStatus.TOMBSTONE,
            },
            MemoryStatus.ARCHIVED: {
                MemoryStatus.TOMBSTONE,
                MemoryStatus.ACTIVE,  # Restore
            },
            MemoryStatus.TOMBSTONE: {
                MemoryStatus.ACTIVE,  # Manual restore only
            },
        }
        return target in valid_transitions.get(self, set())


# =============================================================================
# Lifecycle Stats
# =============================================================================


class LifecycleStats:
    """Statistics from a lifecycle management operation.

    Tracks counts of memories processed by a lifecycle operation.
    """

    def __init__(self) -> None:
        """Initialize empty stats."""
        self.scanned: int = 0
        self.archived: int = 0
        self.tombstoned: int = 0
        self.deleted: int = 0
        self.errors: int = 0
        self.skipped: int = 0

    @property
    def processed(self) -> int:
        """Total memories that were modified."""
        return self.archived + self.tombstoned + self.deleted

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"LifecycleStats(scanned={self.scanned}, archived={self.archived}, "
            f"tombstoned={self.tombstoned}, deleted={self.deleted}, "
            f"errors={self.errors}, skipped={self.skipped})"
        )


# =============================================================================
# Content Compression
# =============================================================================


def compress_content(content: str) -> bytes:
    """Compress content using zlib.

    Args:
        content: The text content to compress.

    Returns:
        Compressed bytes.
    """
    return zlib.compress(content.encode("utf-8"), level=COMPRESSION_LEVEL)


def decompress_content(data: bytes) -> str:
    """Decompress content from zlib bytes.

    Args:
        data: Compressed bytes.

    Returns:
        Decompressed text content.

    Raises:
        ValueError: If decompression fails.
    """
    try:
        return zlib.decompress(data).decode("utf-8")
    except (zlib.error, UnicodeDecodeError) as e:
        raise ValueError(f"Failed to decompress content: {e}") from e


def get_compression_ratio(original: str, compressed: bytes) -> float:
    """Calculate compression ratio.

    Args:
        original: Original text content.
        compressed: Compressed bytes.

    Returns:
        Ratio of compressed size to original size (lower = better).
        Returns 1.0 if original is empty.
    """
    original_size = len(original.encode("utf-8"))
    if original_size == 0:
        return 1.0
    return len(compressed) / original_size


# =============================================================================
# Lifecycle Manager
# =============================================================================


class LifecycleManager:
    """Manages memory lifecycle states and automatic archival.

    The LifecycleManager handles:
    - Manual state transitions (resolve, archive, delete)
    - Automatic archival based on age thresholds
    - Content compression for archived memories
    - Garbage collection for old tombstoned memories

    Example usage:
        manager = LifecycleManager(index_service)

        # Manual transitions
        manager.resolve(memory_id)
        manager.archive(memory_id)
        manager.delete(memory_id)

        # Automatic lifecycle processing
        stats = manager.process_lifecycle()

        # Calculate relevance
        relevance = manager.calculate_relevance(memory)
    """

    def __init__(
        self,
        index_service: IndexService | None = None,
        archive_age_days: float = ARCHIVE_AGE_DAYS,
        tombstone_age_days: float = TOMBSTONE_AGE_DAYS,
        gc_age_days: float = GARBAGE_COLLECTION_AGE_DAYS,
        min_relevance: float = MIN_RELEVANCE_FOR_ACTIVE,
        half_life_days: float = DECAY_HALF_LIFE_DAYS,
    ) -> None:
        """Initialize the LifecycleManager.

        Args:
            index_service: Optional IndexService for database operations.
                If not provided, use set_index_service() before operations.
            archive_age_days: Days before automatic archival.
            tombstone_age_days: Days before automatic tombstoning.
            gc_age_days: Days before garbage collection of tombstones.
            min_relevance: Minimum relevance score to stay active.
            half_life_days: Half-life for temporal decay calculation.
        """
        self._index_service = index_service
        self.archive_age_days = archive_age_days
        self.tombstone_age_days = tombstone_age_days
        self.gc_age_days = gc_age_days
        self.min_relevance = min_relevance
        self.half_life_days = half_life_days

    def set_index_service(self, index_service: IndexService) -> None:
        """Set or update the index service.

        Args:
            index_service: The IndexService to use for database operations.
        """
        self._index_service = index_service

    @property
    def index_service(self) -> IndexService:
        """Get the index service, raising if not configured.

        Raises:
            RuntimeError: If index service not configured.
        """
        if self._index_service is None:
            raise RuntimeError(
                "IndexService not configured. "
                "Call set_index_service() or pass to constructor."
            )
        return self._index_service

    # =========================================================================
    # Relevance Calculation
    # =========================================================================

    def calculate_relevance(self, memory: Memory) -> float:
        """Calculate the current relevance score for a memory.

        Relevance is based on temporal decay using the exponential decay formula.
        Newer memories are more relevant than older ones.

        Args:
            memory: The memory to calculate relevance for.

        Returns:
            Relevance score between 0.0 and 1.0.
        """
        return calculate_temporal_decay(
            memory.timestamp,
            half_life_days=self.half_life_days,
        )

    def get_age_days(self, memory: Memory) -> float:
        """Get the age of a memory in days.

        Args:
            memory: The memory to get age for.

        Returns:
            Age in days as a float.
        """
        return calculate_age_days(memory.timestamp)

    def should_archive(self, memory: Memory) -> bool:
        """Check if a memory should be automatically archived.

        A memory should be archived if:
        - It's currently active or resolved
        - AND either:
          - Its age exceeds archive_age_days
          - OR its relevance is below min_relevance

        Args:
            memory: The memory to check.

        Returns:
            True if the memory should be archived.
        """
        status = MemoryStatus(memory.status)
        if status not in (MemoryStatus.ACTIVE, MemoryStatus.RESOLVED):
            return False

        age_days = self.get_age_days(memory)
        relevance = self.calculate_relevance(memory)

        return age_days >= self.archive_age_days or relevance < self.min_relevance

    def should_tombstone(self, memory: Memory) -> bool:
        """Check if a memory should be automatically tombstoned.

        A memory should be tombstoned if:
        - It's currently archived
        - AND its age exceeds tombstone_age_days

        Args:
            memory: The memory to check.

        Returns:
            True if the memory should be tombstoned.
        """
        status = MemoryStatus(memory.status)
        if status != MemoryStatus.ARCHIVED:
            return False

        age_days = self.get_age_days(memory)
        return age_days >= self.tombstone_age_days

    def should_garbage_collect(self, memory: Memory) -> bool:
        """Check if a tombstoned memory should be garbage collected.

        A memory should be deleted if:
        - It's currently tombstoned
        - AND its age exceeds gc_age_days

        Args:
            memory: The memory to check.

        Returns:
            True if the memory should be deleted.
        """
        status = MemoryStatus(memory.status)
        if status != MemoryStatus.TOMBSTONE:
            return False

        age_days = self.get_age_days(memory)
        return age_days >= self.gc_age_days

    # =========================================================================
    # Manual State Transitions
    # =========================================================================

    def resolve(self, memory_id: str) -> bool:
        """Mark a memory as resolved.

        Transitions an active memory to resolved status.

        Args:
            memory_id: The ID of the memory to resolve.

        Returns:
            True if successful, False if memory not found or invalid transition.
        """
        return self._transition(memory_id, MemoryStatus.RESOLVED)

    def archive(self, memory_id: str, compress: bool = True) -> bool:
        """Archive a memory.

        Transitions a memory to archived status and optionally compresses content.

        Args:
            memory_id: The ID of the memory to archive.
            compress: Whether to compress the content.

        Returns:
            True if successful, False if memory not found or invalid transition.
        """
        return self._transition(
            memory_id, MemoryStatus.ARCHIVED, compress_content_flag=compress
        )

    def delete(self, memory_id: str) -> bool:
        """Mark a memory as tombstoned (soft delete).

        Transitions a memory to tombstone status. The memory can still be
        restored until garbage collection.

        Args:
            memory_id: The ID of the memory to delete.

        Returns:
            True if successful, False if memory not found or invalid transition.
        """
        return self._transition(memory_id, MemoryStatus.TOMBSTONE)

    def restore(self, memory_id: str) -> bool:
        """Restore an archived or tombstoned memory to active status.

        Args:
            memory_id: The ID of the memory to restore.

        Returns:
            True if successful, False if memory not found or invalid transition.
        """
        return self._transition(memory_id, MemoryStatus.ACTIVE)

    def hard_delete(self, memory_id: str) -> bool:
        """Permanently delete a memory from the index.

        This is a destructive operation that cannot be undone.

        Args:
            memory_id: The ID of the memory to permanently delete.

        Returns:
            True if successful, False if memory not found.
        """
        try:
            return self.index_service.delete(memory_id)
        except Exception as e:
            logger.error(f"Failed to hard delete memory {memory_id}: {e}")
            return False

    def _transition(
        self,
        memory_id: str,
        target_status: MemoryStatus,
        compress_content_flag: bool = False,
    ) -> bool:
        """Perform a state transition on a memory.

        Args:
            memory_id: The ID of the memory.
            target_status: The target status.
            compress_content_flag: Whether to compress content (for archival).

        Returns:
            True if successful, False otherwise.
        """
        try:
            memory = self.index_service.get(memory_id)
            if memory is None:
                logger.warning(f"Memory not found for transition: {memory_id}")
                return False

            current_status = MemoryStatus(memory.status)

            # Check valid transition
            if not current_status.can_transition_to(target_status):
                logger.warning(
                    f"Invalid transition {current_status} → {target_status} "
                    f"for memory {memory_id}"
                )
                return False

            # Prepare updated memory
            updates: dict[str, Any] = {"status": target_status.value}

            # Handle archival compression
            if (
                compress_content_flag
                and target_status == MemoryStatus.ARCHIVED
                and not memory.content.startswith(ARCHIVED_CONTENT_PREFIX)
            ):
                # Store compression info in content prefix
                compressed = compress_content(memory.content)
                ratio = get_compression_ratio(memory.content, compressed)
                updates["content"] = (
                    f"{ARCHIVED_CONTENT_PREFIX}"
                    f"[Compressed: {len(compressed)} bytes, "
                    f"ratio: {ratio:.2f}] "
                    f"Original summary: {memory.summary}"
                )

            # Handle tombstone
            if target_status == MemoryStatus.TOMBSTONE:
                updates["summary"] = TOMBSTONE_SUMMARY
                updates["content"] = ""
                updates["tags"] = ()

            updated_memory = replace(memory, **updates)
            return self.index_service.update(updated_memory)

        except Exception as e:
            logger.error(
                f"Failed to transition memory {memory_id} to {target_status}: {e}"
            )
            return False

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def process_lifecycle(
        self,
        dry_run: bool = False,
        spec: str | None = None,
        namespace: str | None = None,
    ) -> LifecycleStats:
        """Process lifecycle transitions for all memories.

        Scans all memories and applies automatic transitions based on
        age thresholds and relevance decay.

        Args:
            dry_run: If True, only report what would be done.
            spec: Optional spec to filter memories.
            namespace: Optional namespace to filter memories.

        Returns:
            LifecycleStats with counts of processed memories.
        """
        stats = LifecycleStats()

        try:
            memories = self._get_memories(spec=spec, namespace=namespace)
        except Exception as e:
            logger.error(f"Failed to retrieve memories for lifecycle: {e}")
            stats.errors += 1
            return stats

        for memory in memories:
            stats.scanned += 1

            try:
                if self.should_garbage_collect(memory):
                    if not dry_run:
                        if self.hard_delete(memory.id):
                            stats.deleted += 1
                        else:
                            stats.errors += 1
                    else:
                        stats.deleted += 1

                elif self.should_tombstone(memory):
                    if not dry_run:
                        if self.delete(memory.id):
                            stats.tombstoned += 1
                        else:
                            stats.errors += 1
                    else:
                        stats.tombstoned += 1

                elif self.should_archive(memory):
                    if not dry_run:
                        if self.archive(memory.id):
                            stats.archived += 1
                        else:
                            stats.errors += 1
                    else:
                        stats.archived += 1

                else:
                    stats.skipped += 1

            except Exception as e:
                logger.error(f"Error processing memory {memory.id}: {e}")
                stats.errors += 1

        return stats

    def archive_batch(
        self,
        memory_ids: Sequence[str],
        compress: bool = True,
    ) -> LifecycleStats:
        """Archive multiple memories at once.

        Args:
            memory_ids: List of memory IDs to archive.
            compress: Whether to compress content.

        Returns:
            LifecycleStats with operation results.
        """
        stats = LifecycleStats()
        stats.scanned = len(memory_ids)

        for memory_id in memory_ids:
            try:
                if self.archive(memory_id, compress=compress):
                    stats.archived += 1
                else:
                    stats.skipped += 1
            except Exception as e:
                logger.error(f"Error archiving memory {memory_id}: {e}")
                stats.errors += 1

        return stats

    def garbage_collect(
        self,
        dry_run: bool = False,
    ) -> LifecycleStats:
        """Run garbage collection on tombstoned memories.

        Args:
            dry_run: If True, only report what would be deleted.

        Returns:
            LifecycleStats with deletion counts.
        """
        stats = LifecycleStats()

        try:
            memories = self._get_memories(status=MemoryStatus.TOMBSTONE)
        except Exception as e:
            logger.error(f"Failed to retrieve tombstoned memories: {e}")
            stats.errors += 1
            return stats

        for memory in memories:
            stats.scanned += 1

            try:
                if self.should_garbage_collect(memory):
                    if not dry_run:
                        if self.hard_delete(memory.id):
                            stats.deleted += 1
                        else:
                            stats.errors += 1
                    else:
                        stats.deleted += 1
                else:
                    stats.skipped += 1

            except Exception as e:
                logger.error(f"Error during garbage collection of {memory.id}: {e}")
                stats.errors += 1

        return stats

    # =========================================================================
    # Query Operations
    # =========================================================================

    def get_stale_memories(
        self,
        max_relevance: float | None = None,
        min_age_days: float | None = None,
    ) -> list[Memory]:
        """Get memories that are becoming stale.

        Args:
            max_relevance: Maximum relevance score (default: min_relevance).
            min_age_days: Minimum age in days.

        Returns:
            List of stale memories sorted by relevance (lowest first).
        """
        if max_relevance is None:
            max_relevance = self.min_relevance

        try:
            memories = self._get_memories(
                status=MemoryStatus.ACTIVE,
            )
        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []

        stale = []
        for memory in memories:
            relevance = self.calculate_relevance(memory)
            age = self.get_age_days(memory)

            meets_relevance = relevance <= max_relevance
            meets_age = min_age_days is None or age >= min_age_days

            if meets_relevance and meets_age:
                stale.append(memory)

        # Sort by relevance (lowest first)
        return sorted(stale, key=lambda m: self.calculate_relevance(m))

    def get_lifecycle_summary(self) -> dict[str, int]:
        """Get summary counts by status.

        Returns:
            Dict mapping status names to counts.
        """
        summary = {
            "active": 0,
            "resolved": 0,
            "archived": 0,
            "tombstone": 0,
            "total": 0,
        }

        try:
            for status in MemoryStatus:
                memories = self._get_memories(status=status)
                count = len(list(memories))
                summary[status.value] = count
                summary["total"] += count
        except Exception as e:
            logger.error(f"Failed to get lifecycle summary: {e}")

        return summary

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _get_memories(
        self,
        spec: str | None = None,
        namespace: str | None = None,
        status: MemoryStatus | None = None,
    ) -> list[Memory]:
        """Get memories with optional filters.

        Args:
            spec: Optional spec filter.
            namespace: Optional namespace filter.
            status: Optional status filter.

        Returns:
            List of matching memories.
        """
        # Get all memories from index
        all_ids = self.index_service.get_all_ids()
        all_memories = self.index_service.get_batch(all_ids)

        result: list[Memory] = []
        for memory in all_memories:
            # Apply filters
            if spec is not None and memory.spec != spec:
                continue
            if namespace is not None and memory.namespace != namespace:
                continue
            if status is not None and memory.status != status.value:
                continue
            result.append(memory)

        return result


# =============================================================================
# Module-Level Singleton
# =============================================================================

_manager: LifecycleManager | None = None


def get_default_manager(
    index_service: IndexService | None = None,
) -> LifecycleManager:
    """Get or create the default LifecycleManager instance.

    Creates a singleton instance on first call. If index_service is provided,
    it will be set on the manager.

    Args:
        index_service: Optional IndexService to configure.

    Returns:
        The singleton LifecycleManager instance.
    """
    global _manager

    if _manager is None:
        _manager = LifecycleManager(index_service=index_service)
    elif index_service is not None:
        _manager.set_index_service(index_service)

    return _manager
