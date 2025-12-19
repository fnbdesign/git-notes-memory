"""Tests for git_notes_memory.recall module.

Tests for RecallService including search operations, hydration levels,
context aggregation, and convenience methods. Uses mocked dependencies
for unit tests and real services for integration tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from git_notes_memory.exceptions import RecallError
from git_notes_memory.models import (
    CommitInfo,
    HydratedMemory,
    HydrationLevel,
    Memory,
    MemoryResult,
    SpecContext,
)
from git_notes_memory.recall import RecallService, get_default_service

if TYPE_CHECKING:
    from git_notes_memory.index import IndexService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_memory() -> Memory:
    """Create a sample Memory for testing."""
    return Memory(
        id="decisions:abc123:0",
        commit_sha="abc123",
        namespace="decisions",
        timestamp=datetime.now(UTC),
        summary="Use PostgreSQL for persistence",
        content="We chose PostgreSQL for its reliability and ACID compliance.",
        spec="SPEC-2025-12-18-001",
        tags=("database", "architecture"),
        phase="implementation",
        status="active",
        relates_to=(),
    )


@pytest.fixture
def sample_memories() -> list[Memory]:
    """Create a list of sample memories for testing."""
    now = datetime.now(UTC)
    return [
        Memory(
            id="decisions:abc123:0",
            commit_sha="abc123",
            namespace="decisions",
            timestamp=now,
            summary="Use PostgreSQL",
            content="PostgreSQL content",
            spec="SPEC-001",
            tags=("database",),
            phase="implementation",
            status="active",
            relates_to=(),
        ),
        Memory(
            id="decisions:abc123:1",
            commit_sha="abc123",
            namespace="decisions",
            timestamp=now,
            summary="Use Redis for caching",
            content="Redis content",
            spec="SPEC-001",
            tags=("caching",),
            phase="implementation",
            status="active",
            relates_to=(),
        ),
        Memory(
            id="learnings:def456:0",
            commit_sha="def456",
            namespace="learnings",
            timestamp=now,
            summary="Type hints improve DX",
            content="Type hints content",
            spec="SPEC-001",
            tags=("python",),
            phase=None,
            status="active",
            relates_to=(),
        ),
    ]


@pytest.fixture
def mock_index() -> MagicMock:
    """Create a mock IndexService."""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_embedding() -> MagicMock:
    """Create a mock EmbeddingService."""
    mock = MagicMock()
    mock.embed.return_value = [0.1] * 384
    return mock


@pytest.fixture
def mock_git_ops() -> MagicMock:
    """Create a mock GitOps instance."""
    mock = MagicMock()
    mock.show_note.return_value = "---\nsummary: Test\n---\nFull note content"
    mock.get_commit_info.return_value = CommitInfo(
        sha="abc123",
        author_name="Test Author",
        author_email="test@example.com",
        date=datetime.now(UTC).isoformat(),
        message="Test commit",
    )
    mock.get_changed_files.return_value = ["file1.py", "file2.py"]
    mock.get_file_at_commit.return_value = "# File content"
    return mock


# =============================================================================
# RecallService Initialization Tests
# =============================================================================


class TestRecallServiceInit:
    """Tests for RecallService initialization."""

    def test_default_init(self) -> None:
        """Test default initialization."""
        service = RecallService()
        assert service._index_service is None
        assert service._embedding_service is None
        assert service._git_ops is None

    def test_init_with_custom_index_path(self, tmp_path: Path) -> None:
        """Test initialization with custom index path."""
        index_path = tmp_path / "custom_index.db"
        service = RecallService(index_path=index_path)
        assert service.index_path == index_path

    def test_init_with_injected_services(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test initialization with injected services."""
        service = RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
            git_ops=mock_git_ops,
        )
        assert service._index_service is mock_index
        assert service._embedding_service is mock_embedding
        assert service._git_ops is mock_git_ops

    def test_lazy_index_creation(self) -> None:
        """Test IndexService is created lazily on first access."""
        # Patch at the source module since recall.py imports locally
        with patch("git_notes_memory.index.IndexService") as mock_index_cls:
            mock_instance = MagicMock()
            mock_index_cls.return_value = mock_instance

            service = RecallService()
            assert service._index_service is None

            # Trigger lazy creation
            _ = service._get_index()
            mock_index_cls.assert_called_once()
            assert service._index_service is mock_instance

    def test_lazy_embedding_creation(self) -> None:
        """Test EmbeddingService is created lazily on first access."""
        # Patch at the source module since recall.py imports locally
        with patch(
            "git_notes_memory.embedding.get_default_service"
        ) as mock_get_default:
            mock_instance = MagicMock()
            mock_get_default.return_value = mock_instance

            service = RecallService()
            assert service._embedding_service is None

            # Trigger lazy creation
            _ = service._get_embedding()
            mock_get_default.assert_called_once()
            assert service._embedding_service is mock_instance

    def test_lazy_git_ops_creation(self) -> None:
        """Test GitOps is created lazily on first access."""
        # Patch at the source module since recall.py imports locally
        with patch("git_notes_memory.git_ops.GitOps") as mock_git_ops_cls:
            mock_instance = MagicMock()
            mock_git_ops_cls.return_value = mock_instance

            service = RecallService()
            assert service._git_ops is None

            # Trigger lazy creation
            _ = service._get_git_ops()
            mock_git_ops_cls.assert_called_once()
            assert service._git_ops is mock_instance


# =============================================================================
# Search Tests
# =============================================================================


class TestRecallServiceSearch:
    """Tests for RecallService.search method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
        sample_memory: Memory,
    ) -> RecallService:
        """Create a RecallService with mocked dependencies."""
        mock_index.search_vector.return_value = [(sample_memory, 0.5)]
        return RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
        )

    def test_basic_search(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
    ) -> None:
        """Test basic semantic search."""
        results = recall_service.search("database recommendations")

        assert len(results) == 1
        assert isinstance(results[0], MemoryResult)
        assert results[0].memory.summary == "Use PostgreSQL for persistence"
        mock_embedding.embed.assert_called_once_with("database recommendations")
        mock_index.search_vector.assert_called_once()

    def test_search_empty_query(self, recall_service: RecallService) -> None:
        """Test search with empty query returns empty list."""
        results = recall_service.search("")
        assert results == []

        results = recall_service.search("   ")
        assert results == []

    def test_search_with_k_parameter(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test search respects k parameter."""
        recall_service.search("test", k=5)
        mock_index.search_vector.assert_called_once()
        call_kwargs = mock_index.search_vector.call_args[1]
        assert call_kwargs["k"] == 5

    def test_search_with_namespace_filter(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test search with namespace filter."""
        recall_service.search("test", namespace="decisions")
        call_kwargs = mock_index.search_vector.call_args[1]
        assert call_kwargs["namespace"] == "decisions"

    def test_search_with_spec_filter(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test search with spec filter."""
        recall_service.search("test", spec="SPEC-001")
        call_kwargs = mock_index.search_vector.call_args[1]
        assert call_kwargs["spec"] == "SPEC-001"

    def test_search_with_min_similarity(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
        sample_memory: Memory,
    ) -> None:
        """Test search filters by minimum similarity."""
        # Return two results with different distances
        memory2 = Memory(
            id="learnings:xyz789:0",
            commit_sha="xyz789",
            namespace="learnings",
            timestamp=datetime.now(UTC),
            summary="Another memory",
            content="Content",
            spec=None,
            tags=(),
            phase=None,
            status="active",
            relates_to=(),
        )
        mock_index.search_vector.return_value = [
            (sample_memory, 0.1),  # High similarity
            (memory2, 5.0),  # Low similarity
        ]

        service = RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
        )

        # With high min_similarity threshold, should filter out the second result
        results = service.search("test", min_similarity=0.5)

        # First result has distance 0.1 -> similarity ≈ 0.91
        # Second result has distance 5.0 -> similarity ≈ 0.17
        assert len(results) == 1
        assert results[0].memory.id == "decisions:abc123:0"

    def test_search_error_handling(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
    ) -> None:
        """Test search handles errors gracefully."""
        mock_index.search_vector.side_effect = Exception("Database error")

        service = RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
        )

        with pytest.raises(RecallError) as exc_info:
            service.search("test")
        assert "Search failed" in exc_info.value.message


class TestRecallServiceSearchText:
    """Tests for RecallService.search_text method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_index: MagicMock,
        sample_memory: Memory,
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.search_text.return_value = [sample_memory]
        return RecallService(index_service=mock_index)

    def test_basic_text_search(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test basic FTS5 text search."""
        results = recall_service.search_text("PostgreSQL")

        assert len(results) == 1
        assert isinstance(results[0], Memory)
        mock_index.search_text.assert_called_once()

    def test_text_search_empty_query(self, recall_service: RecallService) -> None:
        """Test text search with empty query returns empty list."""
        results = recall_service.search_text("")
        assert results == []

    def test_text_search_with_filters(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test text search with namespace and spec filters."""
        recall_service.search_text(
            "test",
            limit=20,
            namespace="decisions",
            spec="SPEC-001",
        )

        call_kwargs = mock_index.search_text.call_args[1]
        assert call_kwargs["namespace"] == "decisions"
        assert call_kwargs["spec"] == "SPEC-001"

    def test_text_search_error_handling(self, mock_index: MagicMock) -> None:
        """Test text search handles errors gracefully."""
        mock_index.search_text.side_effect = Exception("FTS error")

        service = RecallService(index_service=mock_index)

        with pytest.raises(RecallError) as exc_info:
            service.search_text("test")
        assert "Text search failed" in exc_info.value.message


# =============================================================================
# Direct Retrieval Tests
# =============================================================================


class TestRecallServiceGet:
    """Tests for RecallService.get method."""

    @pytest.fixture
    def recall_service(
        self, mock_index: MagicMock, sample_memory: Memory
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.get.return_value = sample_memory
        return RecallService(index_service=mock_index)

    def test_get_existing_memory(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
        sample_memory: Memory,
    ) -> None:
        """Test getting an existing memory by ID."""
        result = recall_service.get("decisions:abc123:0")

        assert result is sample_memory
        mock_index.get.assert_called_once_with("decisions:abc123:0")

    def test_get_nonexistent_memory(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test getting a nonexistent memory returns None."""
        mock_index.get.return_value = None

        result = recall_service.get("decisions:nonexistent:0")
        assert result is None

    def test_get_handles_errors(self, mock_index: MagicMock) -> None:
        """Test get handles errors gracefully and returns None."""
        mock_index.get.side_effect = Exception("Database error")

        service = RecallService(index_service=mock_index)
        result = service.get("decisions:abc123:0")

        assert result is None


class TestRecallServiceGetBatch:
    """Tests for RecallService.get_batch method."""

    @pytest.fixture
    def recall_service(
        self, mock_index: MagicMock, sample_memories: list[Memory]
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.get_batch.return_value = sample_memories[:2]
        return RecallService(index_service=mock_index)

    def test_get_batch(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test getting multiple memories by IDs."""
        ids = ["decisions:abc123:0", "decisions:abc123:1"]
        results = recall_service.get_batch(ids)

        assert len(results) == 2
        mock_index.get_batch.assert_called_once_with(ids)

    def test_get_batch_empty_list(self, recall_service: RecallService) -> None:
        """Test get_batch with empty list returns empty list."""
        results = recall_service.get_batch([])
        assert results == []

    def test_get_batch_handles_errors(self, mock_index: MagicMock) -> None:
        """Test get_batch handles errors gracefully."""
        mock_index.get_batch.side_effect = Exception("Database error")

        service = RecallService(index_service=mock_index)
        results = service.get_batch(["decisions:abc123:0"])

        assert results == []


class TestRecallServiceGetByNamespace:
    """Tests for RecallService.get_by_namespace method."""

    @pytest.fixture
    def recall_service(
        self, mock_index: MagicMock, sample_memories: list[Memory]
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.get_by_namespace.return_value = sample_memories[:2]
        return RecallService(index_service=mock_index)

    def test_get_by_namespace(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test getting memories by namespace."""
        results = recall_service.get_by_namespace("decisions")

        assert len(results) == 2
        mock_index.get_by_namespace.assert_called_once()

    def test_get_by_namespace_with_filters(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test get_by_namespace with spec and limit filters."""
        recall_service.get_by_namespace("decisions", spec="SPEC-001", limit=10)

        call_kwargs = mock_index.get_by_namespace.call_args[1]
        assert call_kwargs["spec"] == "SPEC-001"
        assert call_kwargs["limit"] == 10


class TestRecallServiceGetBySpec:
    """Tests for RecallService.get_by_spec method."""

    @pytest.fixture
    def recall_service(
        self, mock_index: MagicMock, sample_memories: list[Memory]
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.get_by_spec.return_value = sample_memories
        return RecallService(index_service=mock_index)

    def test_get_by_spec(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test getting memories by spec."""
        results = recall_service.get_by_spec("SPEC-001")

        assert len(results) == 3
        mock_index.get_by_spec.assert_called_once()

    def test_get_by_spec_with_filters(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test get_by_spec with namespace and limit filters."""
        recall_service.get_by_spec("SPEC-001", namespace="decisions", limit=5)

        call_kwargs = mock_index.get_by_spec.call_args[1]
        assert call_kwargs["namespace"] == "decisions"
        assert call_kwargs["limit"] == 5


class TestRecallServiceListRecent:
    """Tests for RecallService.list_recent method."""

    @pytest.fixture
    def recall_service(
        self, mock_index: MagicMock, sample_memories: list[Memory]
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.list_recent.return_value = sample_memories
        return RecallService(index_service=mock_index)

    def test_list_recent(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test listing recent memories."""
        results = recall_service.list_recent(limit=10)

        assert len(results) == 3
        assert all(isinstance(r, MemoryResult) for r in results)
        # Distance should be 0.0 for recency-based results
        assert all(r.distance == 0.0 for r in results)

    def test_list_recent_with_filters(
        self,
        recall_service: RecallService,
        mock_index: MagicMock,
    ) -> None:
        """Test list_recent with namespace and spec filters."""
        recall_service.list_recent(
            limit=5,
            namespace="decisions",
            spec="SPEC-001",
        )

        call_kwargs = mock_index.list_recent.call_args[1]
        assert call_kwargs["namespace"] == "decisions"
        assert call_kwargs["spec"] == "SPEC-001"

    def test_list_recent_handles_errors(self, mock_index: MagicMock) -> None:
        """Test list_recent handles errors gracefully."""
        mock_index.list_recent.side_effect = Exception("Database error")

        service = RecallService(index_service=mock_index)
        results = service.list_recent()

        assert results == []


# =============================================================================
# Hydration Tests
# =============================================================================


class TestRecallServiceHydrate:
    """Tests for RecallService.hydrate method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_git_ops: MagicMock,
    ) -> RecallService:
        """Create a RecallService with mocked GitOps."""
        return RecallService(git_ops=mock_git_ops)

    def test_hydrate_summary_level(
        self,
        recall_service: RecallService,
        sample_memory: Memory,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test hydration at SUMMARY level (no additional loading)."""
        result = recall_service.hydrate(sample_memory, HydrationLevel.SUMMARY)

        assert isinstance(result, HydratedMemory)
        assert result.result.memory is sample_memory
        assert result.full_content is None
        assert result.files == ()
        assert result.commit_info is None

        # GitOps should not be called at SUMMARY level
        mock_git_ops.show_note.assert_not_called()

    def test_hydrate_full_level(
        self,
        recall_service: RecallService,
        sample_memory: Memory,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test hydration at FULL level (loads note content)."""
        result = recall_service.hydrate(sample_memory, HydrationLevel.FULL)

        assert result.full_content == "---\nsummary: Test\n---\nFull note content"
        assert result.commit_info is not None
        assert result.commit_info.sha == "abc123"
        assert result.files == ()  # FILES level not requested

        mock_git_ops.show_note.assert_called_once()
        mock_git_ops.get_commit_info.assert_called_once()

    def test_hydrate_files_level(
        self,
        recall_service: RecallService,
        sample_memory: Memory,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test hydration at FILES level (loads file snapshots)."""
        result = recall_service.hydrate(sample_memory, HydrationLevel.FILES)

        assert result.full_content is not None
        assert result.commit_info is not None
        assert len(result.files) == 2
        assert result.files[0] == ("file1.py", "# File content")
        assert result.files[1] == ("file2.py", "# File content")

        mock_git_ops.get_changed_files.assert_called_once()
        assert mock_git_ops.get_file_at_commit.call_count == 2

    def test_hydrate_accepts_memory_result(
        self,
        recall_service: RecallService,
        sample_memory: Memory,
    ) -> None:
        """Test hydrate accepts MemoryResult in addition to Memory."""
        memory_result = MemoryResult(memory=sample_memory, distance=0.5)

        result = recall_service.hydrate(memory_result, HydrationLevel.SUMMARY)

        assert result.result is memory_result
        assert result.result.distance == 0.5

    def test_hydrate_creates_memory_result_from_memory(
        self,
        recall_service: RecallService,
        sample_memory: Memory,
    ) -> None:
        """Test hydrate creates MemoryResult when given raw Memory."""
        result = recall_service.hydrate(sample_memory, HydrationLevel.SUMMARY)

        assert result.result.memory is sample_memory
        assert result.result.distance == 0.0  # Default distance for raw Memory

    def test_hydrate_graceful_commit_info_failure(
        self,
        sample_memory: Memory,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test hydrate continues when commit info fetch fails."""
        mock_git_ops.get_commit_info.side_effect = Exception("Git error")

        service = RecallService(git_ops=mock_git_ops)
        result = service.hydrate(sample_memory, HydrationLevel.FULL)

        # Should still succeed with content but without commit info
        assert result.full_content is not None
        assert result.commit_info is None

    def test_hydrate_error_propagation(
        self,
        sample_memory: Memory,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test hydrate raises RecallError on critical failures."""
        mock_git_ops.show_note.side_effect = Exception("Critical git error")

        service = RecallService(git_ops=mock_git_ops)

        with pytest.raises(RecallError) as exc_info:
            service.hydrate(sample_memory, HydrationLevel.FULL)
        assert "Failed to hydrate memory" in exc_info.value.message


class TestRecallServiceHydrateBatch:
    """Tests for RecallService.hydrate_batch method."""

    @pytest.fixture
    def recall_service(self, mock_git_ops: MagicMock) -> RecallService:
        """Create a RecallService with mocked GitOps."""
        return RecallService(git_ops=mock_git_ops)

    def test_hydrate_batch(
        self,
        recall_service: RecallService,
        sample_memories: list[Memory],
    ) -> None:
        """Test batch hydration."""
        results = recall_service.hydrate_batch(
            sample_memories,
            HydrationLevel.SUMMARY,
        )

        assert len(results) == 3
        assert all(isinstance(r, HydratedMemory) for r in results)

    def test_hydrate_batch_empty_list(self, recall_service: RecallService) -> None:
        """Test batch hydration with empty list."""
        results = recall_service.hydrate_batch([], HydrationLevel.SUMMARY)
        assert results == []


# =============================================================================
# Context Aggregation Tests
# =============================================================================


class TestRecallServiceGetSpecContext:
    """Tests for RecallService.get_spec_context method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_index: MagicMock,
        sample_memories: list[Memory],
    ) -> RecallService:
        """Create a RecallService with mocked index."""
        mock_index.get_by_spec.return_value = sample_memories
        return RecallService(index_service=mock_index)

    def test_get_spec_context(
        self,
        recall_service: RecallService,
    ) -> None:
        """Test getting aggregated context for a spec."""
        ctx = recall_service.get_spec_context("SPEC-001")

        assert isinstance(ctx, SpecContext)
        assert ctx.spec == "SPEC-001"
        assert ctx.total_count == 3
        assert len(ctx.memories) == 3
        assert ctx.token_estimate > 0

    def test_get_spec_context_groups_by_namespace(
        self,
        recall_service: RecallService,
    ) -> None:
        """Test spec context groups memories by namespace."""
        ctx = recall_service.get_spec_context("SPEC-001")

        by_ns = ctx.by_namespace
        assert "decisions" in by_ns
        assert "learnings" in by_ns
        assert len(by_ns["decisions"]) == 2
        assert len(by_ns["learnings"]) == 1

    def test_get_spec_context_empty_spec(
        self,
        mock_index: MagicMock,
    ) -> None:
        """Test get_spec_context for nonexistent spec."""
        mock_index.get_by_spec.return_value = []

        service = RecallService(index_service=mock_index)
        ctx = service.get_spec_context("NONEXISTENT")

        assert ctx.spec == "NONEXISTENT"
        assert ctx.total_count == 0
        assert ctx.memories == ()
        assert ctx.token_estimate == 0

    def test_get_spec_context_handles_errors(
        self,
        mock_index: MagicMock,
    ) -> None:
        """Test get_spec_context handles errors gracefully."""
        mock_index.get_by_spec.side_effect = Exception("Database error")

        service = RecallService(index_service=mock_index)
        ctx = service.get_spec_context("SPEC-001")

        # Should return empty context on error
        assert ctx.spec == "SPEC-001"
        assert ctx.total_count == 0


class TestRecallServiceEstimateTokens:
    """Tests for RecallService._estimate_tokens method."""

    def test_estimate_tokens_summary_level(
        self,
        sample_memories: list[Memory],
    ) -> None:
        """Test token estimation at SUMMARY level."""
        service = RecallService()
        tokens = service._estimate_tokens(sample_memories, HydrationLevel.SUMMARY)

        # Should count summaries + overhead
        assert tokens > 0
        # Each memory has ~15-20 char summary + 50 overhead = ~65-70 chars
        # 3 memories * ~65 chars * 0.25 (TOKENS_PER_CHAR) ≈ 50 tokens
        assert tokens < 200  # Reasonable upper bound for summaries only

    def test_estimate_tokens_full_level(
        self,
        sample_memories: list[Memory],
    ) -> None:
        """Test token estimation at FULL level includes content."""
        service = RecallService()

        summary_tokens = service._estimate_tokens(
            sample_memories, HydrationLevel.SUMMARY
        )
        full_tokens = service._estimate_tokens(sample_memories, HydrationLevel.FULL)

        # FULL should include content, so higher token count
        assert full_tokens > summary_tokens

    def test_estimate_tokens_empty_list(self) -> None:
        """Test token estimation for empty list."""
        service = RecallService()
        tokens = service._estimate_tokens([], HydrationLevel.SUMMARY)
        assert tokens == 0


# =============================================================================
# Convenience Method Tests
# =============================================================================


class TestRecallServiceRecallContext:
    """Tests for RecallService.recall_context convenience method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
        mock_git_ops: MagicMock,
        sample_memory: Memory,
    ) -> RecallService:
        """Create a RecallService with mocked dependencies."""
        mock_index.search_vector.return_value = [(sample_memory, 0.5)]
        return RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
            git_ops=mock_git_ops,
        )

    def test_recall_context(self, recall_service: RecallService) -> None:
        """Test recall_context combines search and hydration."""
        results = recall_service.recall_context(
            "database",
            k=3,
            hydration_level=HydrationLevel.FULL,
        )

        assert len(results) == 1
        assert isinstance(results[0], HydratedMemory)
        assert results[0].full_content is not None

    def test_recall_context_default_hydration(
        self,
        recall_service: RecallService,
        mock_git_ops: MagicMock,
    ) -> None:
        """Test recall_context uses SUMMARY hydration by default."""
        results = recall_service.recall_context("database", k=3)

        assert len(results) == 1
        assert results[0].full_content is None  # SUMMARY level
        mock_git_ops.show_note.assert_not_called()


class TestRecallServiceRecallSimilar:
    """Tests for RecallService.recall_similar method."""

    @pytest.fixture
    def recall_service(
        self,
        mock_index: MagicMock,
        mock_embedding: MagicMock,
        sample_memories: list[Memory],
    ) -> RecallService:
        """Create a RecallService with mocked dependencies."""
        # Return all memories including the original
        mock_index.search_vector.return_value = [
            (sample_memories[0], 0.0),  # Same memory
            (sample_memories[1], 0.3),  # Similar
            (sample_memories[2], 0.7),  # Less similar
        ]
        return RecallService(
            index_service=mock_index,
            embedding_service=mock_embedding,
        )

    def test_recall_similar_excludes_self(
        self,
        recall_service: RecallService,
        sample_memories: list[Memory],
    ) -> None:
        """Test recall_similar excludes the reference memory by default."""
        results = recall_service.recall_similar(sample_memories[0], k=2)

        # Should exclude the original memory
        assert len(results) == 2
        assert all(r.memory.id != sample_memories[0].id for r in results)

    def test_recall_similar_includes_self(
        self,
        recall_service: RecallService,
        sample_memories: list[Memory],
    ) -> None:
        """Test recall_similar can include the reference memory."""
        results = recall_service.recall_similar(
            sample_memories[0],
            k=3,
            exclude_self=False,
        )

        # Should include all results
        assert len(results) == 3

    def test_recall_similar_empty_content(
        self,
        recall_service: RecallService,
    ) -> None:
        """Test recall_similar returns empty for memory without content."""
        memory = Memory(
            id="test:abc:0",
            commit_sha="abc",
            namespace="test",
            timestamp=datetime.now(UTC),
            summary="Test",
            content="",  # Empty content
            spec=None,
            tags=(),
            phase=None,
            status="active",
            relates_to=(),
        )

        results = recall_service.recall_similar(memory)
        assert results == []


# =============================================================================
# Singleton Tests
# =============================================================================


class TestGetDefaultService:
    """Tests for get_default_service singleton."""

    def test_returns_recall_service(self) -> None:
        """Test get_default_service returns a RecallService."""
        # Reset singleton for test
        import git_notes_memory.recall as recall_module

        recall_module._default_service = None

        service = get_default_service()
        assert isinstance(service, RecallService)

    def test_returns_same_instance(self) -> None:
        """Test get_default_service returns the same instance."""
        import git_notes_memory.recall as recall_module

        recall_module._default_service = None

        service1 = get_default_service()
        service2 = get_default_service()
        assert service1 is service2


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.integration
class TestRecallServiceIntegration:
    """Integration tests with real services."""

    @pytest.fixture
    def index_path(self, tmp_path: Path) -> Path:
        """Create a temporary index database path."""
        return tmp_path / "test_index.db"

    @pytest.fixture
    def populated_index(
        self, index_path: Path, sample_memories: list[Memory]
    ) -> Iterator[IndexService]:
        """Create and populate a real IndexService with proper cleanup."""
        from git_notes_memory.index import IndexService

        index = IndexService(index_path)
        index.initialize()  # Must initialize before inserting
        # Insert with dummy embeddings so vector search works
        dummy_embedding = [0.1] * 384
        for memory in sample_memories:
            index.insert(memory, embedding=dummy_embedding)
        yield index
        index.close()  # Properly close the database connection

    def test_search_with_real_index(
        self,
        index_path: Path,
        populated_index: IndexService,
    ) -> None:
        """Test search with real IndexService."""
        # Mock only embedding service to avoid loading model
        mock_embedding = MagicMock()
        mock_embedding.embed.return_value = [0.1] * 384

        service = RecallService(
            index_service=populated_index,
            embedding_service=mock_embedding,
        )

        results = service.search("database", k=5)

        # Should find some results
        assert len(results) > 0

    def test_get_by_spec_with_real_index(
        self,
        index_path: Path,
        populated_index: IndexService,
    ) -> None:
        """Test get_by_spec with real IndexService."""
        service = RecallService(index_service=populated_index)

        results = service.get_by_spec("SPEC-001")

        # All sample memories have spec="SPEC-001"
        assert len(results) == 3

    def test_get_spec_context_with_real_index(
        self,
        index_path: Path,
        populated_index: IndexService,
    ) -> None:
        """Test get_spec_context with real IndexService."""
        service = RecallService(index_service=populated_index)

        ctx = service.get_spec_context("SPEC-001")

        assert ctx.total_count == 3
        assert "decisions" in ctx.by_namespace
        assert "learnings" in ctx.by_namespace
        assert ctx.token_estimate > 0
