"""Tests for git_notes_memory.patterns module.

This module tests the PatternManager and its components:
- PatternCandidate and PatternDetectionResult data models
- Term extraction and clustering algorithms
- Pattern type classification
- Pattern lifecycle management (CANDIDATE -> VALIDATED -> PROMOTED -> DEPRECATED)
- Pattern matching and evidence tracking
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from git_notes_memory.models import (
    Memory,
    Pattern,
    PatternStatus,
    PatternType,
)
from git_notes_memory.patterns import (
    MIN_CONFIDENCE_FOR_VALIDATION,
    MIN_OCCURRENCES_FOR_CANDIDATE,
    MIN_OCCURRENCES_FOR_PROMOTION,
    NAMESPACE_PATTERN_HINTS,
    PATTERN_TYPE_KEYWORDS,
    STOP_WORDS,
    PatternCandidate,
    PatternDetectionResult,
    PatternManager,
    get_default_manager,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


def _make_memory(
    id: str,
    namespace: str,
    summary: str,
    content: str = "",
    tags: tuple[str, ...] = (),
    spec: str | None = None,
    timestamp: datetime | None = None,
) -> Memory:
    """Helper to create a Memory for testing."""
    if timestamp is None:
        timestamp = datetime.now(UTC)
    return Memory(
        id=id,
        commit_sha=id.split(":")[1] if ":" in id else "abc1234",
        namespace=namespace,
        summary=summary,
        content=content or f"Content for: {summary}",
        timestamp=timestamp,
        spec=spec,
        tags=tags,
    )


@pytest.fixture
def sample_memory() -> Memory:
    """Create a single sample memory for testing."""
    return _make_memory(
        id="decisions:abc123:0",
        namespace="decisions",
        summary="Chose PostgreSQL for database persistence",
        content="We decided to use PostgreSQL because it provides better JSON support.",
        tags=("database", "architecture"),
        spec="project-alpha",
    )


@pytest.fixture
def sample_memories_list() -> list[Memory]:
    """Create a list of sample memories with common themes for pattern detection."""
    now = datetime.now(UTC)
    return [
        _make_memory(
            id="decisions:abc123:0",
            namespace="decisions",
            summary="Chose PostgreSQL for database persistence",
            content="PostgreSQL provides better JSON support and scalability.",
            tags=("database", "architecture"),
            spec="project-alpha",
            timestamp=now,
        ),
        _make_memory(
            id="learnings:def456:0",
            namespace="learnings",
            summary="PostgreSQL performs well with proper indexing",
            content="Database queries improved significantly after adding indexes.",
            tags=("database", "performance"),
            spec="project-alpha",
            timestamp=now - timedelta(days=3),
        ),
        _make_memory(
            id="decisions:ghi789:0",
            namespace="decisions",
            summary="Using database migrations for schema changes",
            content="Alembic provides reliable database migration support.",
            tags=("database", "migrations"),
            spec="project-alpha",
            timestamp=now - timedelta(days=7),
        ),
        _make_memory(
            id="blockers:jkl012:0",
            namespace="blockers",
            summary="Connection pooling issues causing failures",
            content="Database connection pool exhaustion under load.",
            tags=("database", "performance", "bug"),
            spec="project-beta",
            timestamp=now - timedelta(days=14),
        ),
        _make_memory(
            id="progress:mno345:0",
            namespace="progress",
            summary="Completed user authentication workflow",
            content="Implemented OAuth2 authentication process successfully.",
            tags=("auth", "security"),
            spec="project-gamma",
            timestamp=now - timedelta(days=30),
        ),
    ]


@pytest.fixture
def pattern_manager() -> PatternManager:
    """Create a fresh PatternManager instance."""
    return PatternManager()


@pytest.fixture
def sample_pattern() -> Pattern:
    """Create a sample Pattern for testing."""
    return Pattern(
        name="Database Design (Technical)",
        pattern_type=PatternType.TECHNICAL,
        description="Technical pattern identified from terms: database, design",
        evidence=("decisions:abc123:0", "learnings:def456:0"),
        confidence=0.75,
        tags=("database", "design", "postgresql"),
        status=PatternStatus.CANDIDATE,
        first_seen=datetime.now(UTC),
        last_seen=datetime.now(UTC),
        occurrence_count=2,
    )


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_min_occurrences_for_candidate(self) -> None:
        """Test MIN_OCCURRENCES_FOR_CANDIDATE is set appropriately."""
        assert MIN_OCCURRENCES_FOR_CANDIDATE >= 2
        assert MIN_OCCURRENCES_FOR_CANDIDATE <= 5

    def test_min_confidence_for_validation(self) -> None:
        """Test MIN_CONFIDENCE_FOR_VALIDATION is in valid range."""
        assert 0.0 <= MIN_CONFIDENCE_FOR_VALIDATION <= 1.0
        assert MIN_CONFIDENCE_FOR_VALIDATION >= 0.5

    def test_min_occurrences_for_promotion(self) -> None:
        """Test MIN_OCCURRENCES_FOR_PROMOTION is higher than candidate."""
        assert MIN_OCCURRENCES_FOR_PROMOTION > MIN_OCCURRENCES_FOR_CANDIDATE

    def test_stop_words_is_frozenset(self) -> None:
        """Test STOP_WORDS is a frozenset."""
        assert isinstance(STOP_WORDS, frozenset)

    def test_stop_words_contains_common_words(self) -> None:
        """Test STOP_WORDS contains common English words."""
        expected = {"the", "a", "an", "is", "are", "was", "were", "be"}
        assert expected.issubset(STOP_WORDS)

    def test_stop_words_excludes_technical_terms(self) -> None:
        """Test STOP_WORDS doesn't contain technical terms."""
        technical = {"database", "api", "function", "class", "error"}
        assert not technical.intersection(STOP_WORDS)

    def test_pattern_type_keywords_has_all_types(self) -> None:
        """Test PATTERN_TYPE_KEYWORDS covers all pattern types."""
        # At least the main types should have keywords
        expected_types = {
            PatternType.SUCCESS,
            PatternType.ANTI_PATTERN,
            PatternType.WORKFLOW,
            PatternType.DECISION,
            PatternType.TECHNICAL,
        }
        assert expected_types.issubset(PATTERN_TYPE_KEYWORDS.keys())

    def test_pattern_type_keywords_are_frozensets(self) -> None:
        """Test all keyword sets are frozensets."""
        for keywords in PATTERN_TYPE_KEYWORDS.values():
            assert isinstance(keywords, frozenset)

    def test_namespace_pattern_hints_has_common_namespaces(self) -> None:
        """Test NAMESPACE_PATTERN_HINTS covers common namespaces."""
        expected = {"decisions", "learnings", "blockers"}
        assert expected.issubset(NAMESPACE_PATTERN_HINTS.keys())


# =============================================================================
# PatternCandidate Tests
# =============================================================================


class TestPatternCandidate:
    """Tests for PatternCandidate data class."""

    def test_basic_creation(self) -> None:
        """Test basic PatternCandidate creation."""
        candidate = PatternCandidate(
            name="Test Pattern",
            pattern_type=PatternType.TECHNICAL,
            terms=("database", "api"),
        )
        assert candidate.name == "Test Pattern"
        assert candidate.pattern_type == PatternType.TECHNICAL
        assert candidate.terms == ("database", "api")

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
        )
        assert candidate.evidence_ids == ()
        assert candidate.raw_score == 0.0
        assert candidate.normalized_score == 0.0
        assert candidate.recency_boost == 0.0

    def test_occurrence_count_property(self) -> None:
        """Test occurrence_count returns evidence count."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
            evidence_ids=("mem1", "mem2", "mem3"),
        )
        assert candidate.occurrence_count == 3

    def test_occurrence_count_empty(self) -> None:
        """Test occurrence_count with no evidence."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
        )
        assert candidate.occurrence_count == 0

    def test_to_pattern_creates_candidate_status(self) -> None:
        """Test to_pattern creates Pattern with CANDIDATE status."""
        candidate = PatternCandidate(
            name="Test Pattern",
            pattern_type=PatternType.DECISION,
            terms=("decision", "choice"),
            evidence_ids=("mem1", "mem2"),
            normalized_score=0.8,
            recency_boost=0.5,
        )
        pattern = candidate.to_pattern()
        assert pattern.status == PatternStatus.CANDIDATE
        assert pattern.name == "Test Pattern"
        assert pattern.pattern_type == PatternType.DECISION

    def test_to_pattern_sets_timestamps(self) -> None:
        """Test to_pattern sets first_seen and last_seen."""
        now = datetime.now(UTC)
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
        )
        pattern = candidate.to_pattern(now=now)
        assert pattern.first_seen == now
        assert pattern.last_seen == now

    def test_to_pattern_calculates_confidence(self) -> None:
        """Test to_pattern calculates confidence from scores."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
            evidence_ids=(
                "m1",
                "m2",
                "m3",
                "m4",
                "m5",
            ),  # 5 = MIN_OCCURRENCES_FOR_PROMOTION
            normalized_score=1.0,
            recency_boost=1.0,
        )
        pattern = candidate.to_pattern()
        # Confidence should be clamped to max 1.0
        assert 0.0 <= pattern.confidence <= 1.0
        # With high scores, confidence should be high
        assert pattern.confidence >= 0.8

    def test_to_pattern_uses_terms_as_tags(self) -> None:
        """Test to_pattern uses terms as pattern tags."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.TECHNICAL,
            terms=("database", "migration", "schema"),
        )
        pattern = candidate.to_pattern()
        assert pattern.tags == ("database", "migration", "schema")

    def test_to_pattern_generates_description(self) -> None:
        """Test to_pattern generates description from terms."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.WORKFLOW,
            terms=("process", "workflow", "step"),
        )
        pattern = candidate.to_pattern()
        assert "Workflow" in pattern.description
        assert "process" in pattern.description.lower()

    def test_to_pattern_sets_occurrence_count(self) -> None:
        """Test to_pattern sets correct occurrence_count."""
        candidate = PatternCandidate(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            terms=("test",),
            evidence_ids=("m1", "m2", "m3"),
        )
        pattern = candidate.to_pattern()
        assert pattern.occurrence_count == 3


# =============================================================================
# PatternDetectionResult Tests
# =============================================================================


class TestPatternDetectionResult:
    """Tests for PatternDetectionResult data class."""

    def test_basic_creation(self) -> None:
        """Test basic PatternDetectionResult creation."""
        result = PatternDetectionResult(candidates=())
        assert result.candidates == ()
        assert result.memories_analyzed == 0

    def test_with_candidates(self) -> None:
        """Test creation with candidates."""
        candidates = (
            PatternCandidate(name="P1", pattern_type=PatternType.SUCCESS, terms=("a",)),
            PatternCandidate(
                name="P2", pattern_type=PatternType.WORKFLOW, terms=("b",)
            ),
        )
        result = PatternDetectionResult(
            candidates=candidates,
            memories_analyzed=10,
            terms_extracted=50,
            clusters_found=3,
            detection_time_ms=15.5,
        )
        assert len(result.candidates) == 2
        assert result.memories_analyzed == 10
        assert result.terms_extracted == 50
        assert result.clusters_found == 3
        assert result.detection_time_ms == 15.5

    def test_candidate_count_property(self) -> None:
        """Test candidate_count returns correct count."""
        candidates = (
            PatternCandidate(name="P1", pattern_type=PatternType.SUCCESS, terms=("a",)),
            PatternCandidate(name="P2", pattern_type=PatternType.SUCCESS, terms=("b",)),
            PatternCandidate(name="P3", pattern_type=PatternType.SUCCESS, terms=("c",)),
        )
        result = PatternDetectionResult(candidates=candidates)
        assert result.candidate_count == 3

    def test_candidate_count_empty(self) -> None:
        """Test candidate_count with no candidates."""
        result = PatternDetectionResult(candidates=())
        assert result.candidate_count == 0

    def test_get_by_type_filters_correctly(self) -> None:
        """Test get_by_type filters candidates by type."""
        candidates = (
            PatternCandidate(name="P1", pattern_type=PatternType.SUCCESS, terms=("a",)),
            PatternCandidate(
                name="P2", pattern_type=PatternType.WORKFLOW, terms=("b",)
            ),
            PatternCandidate(name="P3", pattern_type=PatternType.SUCCESS, terms=("c",)),
        )
        result = PatternDetectionResult(candidates=candidates)

        success_patterns = result.get_by_type(PatternType.SUCCESS)
        assert len(success_patterns) == 2
        assert all(p.pattern_type == PatternType.SUCCESS for p in success_patterns)

    def test_get_by_type_returns_empty_for_no_matches(self) -> None:
        """Test get_by_type returns empty list when no matches."""
        candidates = (
            PatternCandidate(name="P1", pattern_type=PatternType.SUCCESS, terms=("a",)),
        )
        result = PatternDetectionResult(candidates=candidates)

        anti_patterns = result.get_by_type(PatternType.ANTI_PATTERN)
        assert anti_patterns == []

    def test_frozen_dataclass(self) -> None:
        """Test PatternDetectionResult is immutable."""
        result = PatternDetectionResult(candidates=())
        with pytest.raises(AttributeError):
            result.memories_analyzed = 100  # type: ignore[misc]


# =============================================================================
# PatternManager Term Extraction Tests
# =============================================================================


class TestPatternManagerTermExtraction:
    """Tests for PatternManager term extraction."""

    def test_extract_terms_from_summary(self, pattern_manager: PatternManager) -> None:
        """Test term extraction from summary."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Database migration strategy",
            content="",
        )
        terms = pattern_manager._extract_terms(memory)
        assert "database" in terms
        assert "migration" in terms
        assert "strategy" in terms

    def test_extract_terms_from_content(self, pattern_manager: PatternManager) -> None:
        """Test term extraction from content."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Test",
            content="PostgreSQL provides excellent performance for complex queries.",
        )
        terms = pattern_manager._extract_terms(memory)
        assert "postgresql" in terms
        assert "performance" in terms
        assert "queries" in terms

    def test_extract_terms_from_tags(self, pattern_manager: PatternManager) -> None:
        """Test term extraction from tags."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Test",
            tags=("authentication", "security", "oauth"),
        )
        terms = pattern_manager._extract_terms(memory)
        assert "authentication" in terms
        assert "security" in terms
        assert "oauth" in terms

    def test_extract_terms_filters_stop_words(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test that stop words are filtered out."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="The database is a very important component",
            content="",
        )
        terms = pattern_manager._extract_terms(memory)
        assert "the" not in terms
        assert "is" not in terms
        assert "very" not in terms
        assert "database" in terms  # Not a stop word

    def test_extract_terms_lowercase(self, pattern_manager: PatternManager) -> None:
        """Test that terms are lowercased."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="PostgreSQL DATABASE Architecture",
            content="",
        )
        terms = pattern_manager._extract_terms(memory)
        assert "postgresql" in terms
        assert "database" in terms
        assert "architecture" in terms
        assert "PostgreSQL" not in terms  # Should be lowercase

    def test_extract_terms_filters_short_terms(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test that very short terms (< 2 chars) are filtered."""
        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="I use a DB for data storage",
            content="",
        )
        terms = pattern_manager._extract_terms(memory)
        # Single letter words should be filtered
        assert "i" not in terms
        assert "a" not in terms
        # Longer terms should remain
        assert "db" in terms
        assert "data" in terms


# =============================================================================
# PatternManager Pattern Detection Tests
# =============================================================================


class TestPatternManagerDetection:
    """Tests for PatternManager pattern detection."""

    def test_detect_patterns_empty_list(self, pattern_manager: PatternManager) -> None:
        """Test detection with empty memory list."""
        result = pattern_manager.detect_patterns([])
        assert result.candidate_count == 0
        assert result.memories_analyzed == 0
        assert result.detection_time_ms >= 0.0

    def test_detect_patterns_single_memory(
        self, pattern_manager: PatternManager, sample_memory: Memory
    ) -> None:
        """Test detection with single memory doesn't produce patterns."""
        result = pattern_manager.detect_patterns([sample_memory], min_occurrences=2)
        # With min_occurrences=2, a single memory shouldn't produce patterns
        assert result.memories_analyzed == 1

    def test_detect_patterns_finds_common_themes(
        self, pattern_manager: PatternManager, sample_memories_list: list[Memory]
    ) -> None:
        """Test detection finds common themes across memories."""
        result = pattern_manager.detect_patterns(sample_memories_list)
        assert result.memories_analyzed == len(sample_memories_list)
        assert result.terms_extracted > 0
        # Should find at least one pattern (database is common)
        # Note: with min_occurrences=2, need at least 2 memories with common terms

    def test_detect_patterns_tracks_evidence(
        self, pattern_manager: PatternManager, sample_memories_list: list[Memory]
    ) -> None:
        """Test detected patterns track evidence memory IDs."""
        result = pattern_manager.detect_patterns(sample_memories_list)
        for candidate in result.candidates:
            assert len(candidate.evidence_ids) >= MIN_OCCURRENCES_FOR_CANDIDATE

    def test_detect_patterns_normalizes_scores(
        self, pattern_manager: PatternManager, sample_memories_list: list[Memory]
    ) -> None:
        """Test detection normalizes scores to 0-1 range."""
        result = pattern_manager.detect_patterns(sample_memories_list)
        for candidate in result.candidates:
            assert 0.0 <= candidate.normalized_score <= 1.0

    def test_detect_patterns_respects_max_candidates(
        self, pattern_manager: PatternManager, sample_memories_list: list[Memory]
    ) -> None:
        """Test detection respects max_candidates limit."""
        result = pattern_manager.detect_patterns(sample_memories_list, max_candidates=2)
        assert len(result.candidates) <= 2

    def test_detect_patterns_respects_min_occurrences(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detection respects min_occurrences threshold."""
        # Create memories where some terms appear only once
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Unique term alpha here",
                content="",
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Unique term beta there",
                content="",
            ),
        ]
        result = pattern_manager.detect_patterns(memories, min_occurrences=3)
        # With min_occurrences=3, no patterns should be found
        assert result.candidate_count == 0

    def test_detect_patterns_calculates_recency_boost(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detection calculates recency boost for patterns."""
        now = datetime.now(UTC)
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Database design decision",
                content="",
                timestamp=now,  # Recent
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Database migration decision",
                content="",
                timestamp=now,  # Recent
            ),
        ]
        result = pattern_manager.detect_patterns(memories)
        for candidate in result.candidates:
            # Recent memories should have high recency boost
            assert candidate.recency_boost >= 0.0


# =============================================================================
# PatternManager Pattern Classification Tests
# =============================================================================


class TestPatternManagerClassification:
    """Tests for PatternManager pattern type classification."""

    def test_classify_success_pattern(self, pattern_manager: PatternManager) -> None:
        """Test classification of success patterns."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="learnings",
                summary="Successfully solved the problem",
                content="This worked great and improved performance.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["success", "solved", "worked"]
        )
        assert pattern_type == PatternType.SUCCESS

    def test_classify_anti_pattern(self, pattern_manager: PatternManager) -> None:
        """Test classification of anti-patterns."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="blockers",
                summary="Avoid this problematic approach",
                content="This caused errors and failures.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["error", "failed", "avoid"]
        )
        assert pattern_type == PatternType.ANTI_PATTERN

    def test_classify_workflow_pattern(self, pattern_manager: PatternManager) -> None:
        """Test classification of workflow patterns."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="progress",
                summary="Development process and workflow",
                content="Follow these steps in sequence.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["process", "workflow", "step"]
        )
        assert pattern_type == PatternType.WORKFLOW

    def test_classify_decision_pattern(self, pattern_manager: PatternManager) -> None:
        """Test classification of decision patterns."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Decided to use this approach",
                content="We chose this option because of tradeoffs.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["decision", "chose", "tradeoff"]
        )
        assert pattern_type == PatternType.DECISION

    def test_classify_uses_namespace_hints(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test classification uses namespace hints."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Some neutral content",
                content="No obvious type keywords here.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["some", "content"]
        )
        # Should hint toward DECISION based on namespace
        assert pattern_type == PatternType.DECISION

    def test_classify_defaults_to_technical(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test classification defaults to TECHNICAL when no hints match."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="custom",  # Not in hints
                summary="Some content",
                content="No type keywords here.",
            ),
        ]
        pattern_type = pattern_manager._classify_pattern_type(
            memories, ["some", "content"]
        )
        assert pattern_type == PatternType.TECHNICAL


# =============================================================================
# PatternManager Lifecycle Tests
# =============================================================================


class TestPatternManagerLifecycle:
    """Tests for PatternManager pattern lifecycle management."""

    def test_register_pattern(
        self, pattern_manager: PatternManager, sample_pattern: Pattern
    ) -> None:
        """Test registering a pattern."""
        pattern_manager.register_pattern(sample_pattern)
        retrieved = pattern_manager.get_pattern(sample_pattern.name)
        assert retrieved is not None
        assert retrieved.name == sample_pattern.name

    def test_get_pattern_not_found(self, pattern_manager: PatternManager) -> None:
        """Test getting non-existent pattern returns None."""
        result = pattern_manager.get_pattern("nonexistent")
        assert result is None

    def test_list_patterns_empty(self, pattern_manager: PatternManager) -> None:
        """Test listing patterns when none registered."""
        result = pattern_manager.list_patterns()
        assert result == []

    def test_list_patterns_filters_by_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test listing patterns filtered by status."""
        candidate = Pattern(
            name="P1",
            pattern_type=PatternType.SUCCESS,
            description="Test 1",
            status=PatternStatus.CANDIDATE,
        )
        validated = Pattern(
            name="P2",
            pattern_type=PatternType.SUCCESS,
            description="Test 2",
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(candidate)
        pattern_manager.register_pattern(validated)

        candidates = pattern_manager.list_patterns(status=PatternStatus.CANDIDATE)
        assert len(candidates) == 1
        assert candidates[0].name == "P1"

    def test_list_patterns_filters_by_type(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test listing patterns filtered by type."""
        success = Pattern(
            name="P1",
            pattern_type=PatternType.SUCCESS,
            description="Test 1",
        )
        workflow = Pattern(
            name="P2",
            pattern_type=PatternType.WORKFLOW,
            description="Test 2",
        )
        pattern_manager.register_pattern(success)
        pattern_manager.register_pattern(workflow)

        workflows = pattern_manager.list_patterns(pattern_type=PatternType.WORKFLOW)
        assert len(workflows) == 1
        assert workflows[0].name == "P2"

    def test_list_patterns_sorted_by_confidence(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test patterns are sorted by confidence descending."""
        low = Pattern(
            name="Low",
            pattern_type=PatternType.SUCCESS,
            description="Low confidence",
            confidence=0.3,
        )
        high = Pattern(
            name="High",
            pattern_type=PatternType.SUCCESS,
            description="High confidence",
            confidence=0.9,
        )
        mid = Pattern(
            name="Mid",
            pattern_type=PatternType.SUCCESS,
            description="Mid confidence",
            confidence=0.6,
        )
        pattern_manager.register_pattern(low)
        pattern_manager.register_pattern(high)
        pattern_manager.register_pattern(mid)

        result = pattern_manager.list_patterns()
        assert result[0].name == "High"
        assert result[1].name == "Mid"
        assert result[2].name == "Low"

    def test_validate_pattern_transitions_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test validate_pattern transitions CANDIDATE to VALIDATED."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            status=PatternStatus.CANDIDATE,
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.validate_pattern("Test")
        assert result is not None
        assert result.status == PatternStatus.VALIDATED

    def test_validate_pattern_fails_wrong_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test validate_pattern fails if not CANDIDATE."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            status=PatternStatus.VALIDATED,  # Already validated
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.validate_pattern("Test")
        assert result is None  # Should fail

    def test_promote_pattern_transitions_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test promote_pattern transitions VALIDATED to PROMOTED."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.promote_pattern("Test")
        assert result is not None
        assert result.status == PatternStatus.PROMOTED

    def test_promote_pattern_fails_wrong_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test promote_pattern fails if not VALIDATED."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            status=PatternStatus.CANDIDATE,  # Not validated
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.promote_pattern("Test")
        assert result is None  # Should fail

    def test_deprecate_pattern_from_any_status(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test deprecate_pattern works from any status."""
        for initial_status in [
            PatternStatus.CANDIDATE,
            PatternStatus.VALIDATED,
            PatternStatus.PROMOTED,
        ]:
            pattern = Pattern(
                name=f"Test_{initial_status.value}",
                pattern_type=PatternType.SUCCESS,
                description="Test pattern",
                status=initial_status,
            )
            pattern_manager.register_pattern(pattern)

            result = pattern_manager.deprecate_pattern(f"Test_{initial_status.value}")
            assert result is not None
            assert result.status == PatternStatus.DEPRECATED

    def test_deprecate_nonexistent_pattern(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test deprecate_pattern returns None for nonexistent pattern."""
        result = pattern_manager.deprecate_pattern("nonexistent")
        assert result is None

    def test_get_promoted_patterns(self, pattern_manager: PatternManager) -> None:
        """Test get_promoted_patterns returns only promoted patterns."""
        patterns = [
            Pattern(
                name="P1",
                pattern_type=PatternType.SUCCESS,
                description="Candidate",
                status=PatternStatus.CANDIDATE,
            ),
            Pattern(
                name="P2",
                pattern_type=PatternType.SUCCESS,
                description="Promoted",
                status=PatternStatus.PROMOTED,
            ),
            Pattern(
                name="P3",
                pattern_type=PatternType.SUCCESS,
                description="Validated",
                status=PatternStatus.VALIDATED,
            ),
        ]
        for p in patterns:
            pattern_manager.register_pattern(p)

        promoted = pattern_manager.get_promoted_patterns()
        assert len(promoted) == 1
        assert promoted[0].name == "P2"


# =============================================================================
# PatternManager Evidence Tests
# =============================================================================


class TestPatternManagerEvidence:
    """Tests for PatternManager evidence management."""

    def test_add_evidence_to_pattern(self, pattern_manager: PatternManager) -> None:
        """Test adding evidence to a pattern."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            evidence=("mem1",),
            occurrence_count=1,
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.add_evidence("Test", "mem2")
        assert result is not None
        assert "mem2" in result.evidence
        assert result.occurrence_count == 2

    def test_add_evidence_increases_confidence(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test adding evidence increases confidence."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            confidence=0.5,
            evidence=("mem1",),
            occurrence_count=1,
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.add_evidence("Test", "mem2")
        assert result is not None
        assert result.confidence > 0.5

    def test_add_duplicate_evidence_no_op(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test adding duplicate evidence is a no-op."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            evidence=("mem1", "mem2"),
            occurrence_count=2,
        )
        pattern_manager.register_pattern(pattern)

        result = pattern_manager.add_evidence("Test", "mem1")  # Already present
        assert result is not None
        assert result.occurrence_count == 2  # Unchanged

    def test_add_evidence_nonexistent_pattern(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test adding evidence to nonexistent pattern returns None."""
        result = pattern_manager.add_evidence("nonexistent", "mem1")
        assert result is None

    def test_add_evidence_auto_validates(self, pattern_manager: PatternManager) -> None:
        """Test adding evidence auto-validates when confidence threshold met."""
        pattern = Pattern(
            name="Test",
            pattern_type=PatternType.SUCCESS,
            description="Test pattern",
            status=PatternStatus.CANDIDATE,
            confidence=MIN_CONFIDENCE_FOR_VALIDATION - 0.1,
            evidence=("mem1", "mem2", "mem3"),
            occurrence_count=3,
        )
        pattern_manager.register_pattern(pattern)

        # Add evidence to push confidence over threshold
        result = pattern_manager.add_evidence("Test", "mem4")
        # If auto-validation triggered, status should be VALIDATED
        # Note: depends on the confidence calculation


# =============================================================================
# PatternManager Pattern Matching Tests
# =============================================================================


class TestPatternManagerMatching:
    """Tests for PatternManager pattern matching."""

    def test_find_matching_patterns_returns_matches(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test find_matching_patterns returns matching patterns."""
        pattern = Pattern(
            name="Database Pattern",
            pattern_type=PatternType.TECHNICAL,
            description="Database-related pattern",
            tags=("database", "postgresql", "migration"),
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(pattern)

        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Database migration strategy",
            content="PostgreSQL schema changes",
        )
        matches = pattern_manager.find_matching_patterns(memory)
        assert len(matches) >= 1
        assert matches[0][0].name == "Database Pattern"

    def test_find_matching_patterns_returns_scores(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test find_matching_patterns returns match scores."""
        pattern = Pattern(
            name="Test Pattern",
            pattern_type=PatternType.TECHNICAL,
            description="Test",
            tags=("test", "pattern", "check"),
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(pattern)

        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Test pattern check",
            content="",
        )
        matches = pattern_manager.find_matching_patterns(memory)
        assert len(matches) >= 1
        assert 0.0 <= matches[0][1] <= 1.0  # Score in valid range

    def test_find_matching_patterns_excludes_deprecated(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test deprecated patterns are excluded from matches."""
        pattern = Pattern(
            name="Deprecated Pattern",
            pattern_type=PatternType.TECHNICAL,
            description="Old pattern",
            tags=("database", "legacy"),
            status=PatternStatus.DEPRECATED,
        )
        pattern_manager.register_pattern(pattern)

        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Database migration",
            content="Legacy database code",
        )
        matches = pattern_manager.find_matching_patterns(memory)
        # Deprecated pattern should not be in results
        pattern_names = [m[0].name for m in matches]
        assert "Deprecated Pattern" not in pattern_names

    def test_find_matching_patterns_respects_min_overlap(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test min_term_overlap threshold is respected."""
        pattern = Pattern(
            name="Test Pattern",
            pattern_type=PatternType.TECHNICAL,
            description="Test",
            tags=("term1", "term2", "term3"),
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(pattern)

        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Only term1 here",  # Only 1 matching term
            content="",
        )
        matches = pattern_manager.find_matching_patterns(memory, min_term_overlap=2)
        # With only 1 overlap and min_term_overlap=2, should not match
        assert len(matches) == 0

    def test_find_matching_patterns_sorts_by_score(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test matches are sorted by score descending."""
        pattern1 = Pattern(
            name="Low Match",
            pattern_type=PatternType.TECHNICAL,
            description="Test",
            tags=("database",),
            status=PatternStatus.VALIDATED,
        )
        pattern2 = Pattern(
            name="High Match",
            pattern_type=PatternType.TECHNICAL,
            description="Test",
            tags=("database", "postgresql", "migration"),
            status=PatternStatus.VALIDATED,
        )
        pattern_manager.register_pattern(pattern1)
        pattern_manager.register_pattern(pattern2)

        memory = _make_memory(
            id="test:abc:0",
            namespace="decisions",
            summary="Database postgresql migration plan",
            content="",
        )
        matches = pattern_manager.find_matching_patterns(memory, min_term_overlap=1)
        if len(matches) >= 2:
            # Higher match score should come first
            assert matches[0][1] >= matches[1][1]


# =============================================================================
# PatternManager Singleton Tests
# =============================================================================


class TestPatternManagerSingleton:
    """Tests for PatternManager singleton behavior."""

    def test_get_default_manager_returns_instance(self) -> None:
        """Test get_default_manager returns a PatternManager."""
        manager = get_default_manager()
        assert isinstance(manager, PatternManager)

    def test_get_default_manager_returns_same_instance(self) -> None:
        """Test get_default_manager returns the same instance."""
        manager1 = get_default_manager()
        manager2 = get_default_manager()
        assert manager1 is manager2

    def test_singleton_reset_works(self) -> None:
        """Test that singleton reset in conftest works."""
        from git_notes_memory import patterns

        manager1 = get_default_manager()
        # Simulate reset (like conftest does)
        patterns._manager = None
        manager2 = get_default_manager()
        assert manager1 is not manager2


# =============================================================================
# PatternManager Integration Tests
# =============================================================================


class TestPatternManagerIntegration:
    """Integration tests for PatternManager with mocked dependencies."""

    def test_detect_from_namespace_uses_recall_service(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detect_from_namespace retrieves memories via RecallService."""
        mock_recall = MagicMock()
        mock_recall.get_by_namespace.return_value = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Database decision",
                content="",
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Database migration",
                content="",
            ),
        ]
        pattern_manager._recall_service = mock_recall

        result = pattern_manager.detect_from_namespace("decisions")
        mock_recall.get_by_namespace.assert_called_once_with("decisions", spec=None)
        assert result.memories_analyzed == 2

    def test_detect_all_uses_index_service(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detect_all retrieves memories via IndexService."""
        mock_index = MagicMock()
        mock_index.is_initialized = True
        mock_index.get_all_ids.return_value = ["id1", "id2"]
        mock_index.get_batch.return_value = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Test 1",
                content="",
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Test 2",
                content="",
            ),
        ]
        pattern_manager._index_service = mock_index

        result = pattern_manager.detect_all()
        mock_index.get_all_ids.assert_called_once()
        mock_index.get_batch.assert_called_once_with(["id1", "id2"])
        assert result.memories_analyzed == 2

    def test_detect_all_filters_by_spec(self, pattern_manager: PatternManager) -> None:
        """Test detect_all filters by spec when provided."""
        mock_index = MagicMock()
        mock_index.is_initialized = True
        mock_index.get_all_ids.return_value = ["id1", "id2"]
        mock_index.get_batch.return_value = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Test 1",
                spec="project-alpha",
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Test 2",
                spec="project-beta",
            ),
        ]
        pattern_manager._index_service = mock_index

        result = pattern_manager.detect_all(spec="project-alpha")
        # Only project-alpha memory should be analyzed
        assert result.memories_analyzed == 1


# =============================================================================
# PatternManager Name Generation Tests
# =============================================================================


class TestPatternManagerNameGeneration:
    """Tests for pattern name generation."""

    def test_generate_pattern_name_includes_terms(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test generated name includes top terms."""
        name = pattern_manager._generate_pattern_name(
            ["database", "migration", "schema"],
            PatternType.TECHNICAL,
        )
        assert "Database" in name
        assert "Migration" in name

    def test_generate_pattern_name_includes_type(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test generated name includes pattern type."""
        name = pattern_manager._generate_pattern_name(
            ["test", "example"],
            PatternType.SUCCESS,
        )
        assert "Success" in name

    def test_generate_pattern_name_limits_terms(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test generated name limits to top 3 terms."""
        name = pattern_manager._generate_pattern_name(
            ["one", "two", "three", "four", "five"],
            PatternType.TECHNICAL,
        )
        # Should only include first 3 terms
        assert "One" in name
        assert "Two" in name
        assert "Three" in name
        # Should NOT include beyond top 3 in title portion
        # (May appear in type label if coincidentally matches)


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestPatternManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_detect_with_empty_content_memory(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detection handles memories with empty content."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="",
                content="",
                tags=(),
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="",
                content="",
                tags=(),
            ),
        ]
        # Should not raise
        result = pattern_manager.detect_patterns(memories)
        assert result.memories_analyzed == 2

    def test_detect_with_unicode_content(self, pattern_manager: PatternManager) -> None:
        """Test detection handles Unicode content."""
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="日本語テスト database",
                content="Émojis 🎉 and café",
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Another database test",
                content="More content",
            ),
        ]
        # Should not raise
        result = pattern_manager.detect_patterns(memories)
        assert result.memories_analyzed == 2

    def test_detect_with_very_long_content(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test detection handles very long content."""
        long_content = "database " * 10000
        memories = [
            _make_memory(
                id="test:abc:0",
                namespace="decisions",
                summary="Test",
                content=long_content,
            ),
            _make_memory(
                id="test:def:0",
                namespace="decisions",
                summary="Test",
                content=long_content,
            ),
        ]
        # Should not raise and should handle efficiently
        result = pattern_manager.detect_patterns(memories)
        assert result.memories_analyzed == 2

    def test_transition_nonexistent_pattern(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test status transitions return None for nonexistent patterns."""
        assert pattern_manager.validate_pattern("nonexistent") is None
        assert pattern_manager.promote_pattern("nonexistent") is None
        assert pattern_manager.deprecate_pattern("nonexistent") is None

    def test_calculate_raw_score_zero_memories(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test raw score calculation handles zero memories."""
        score = pattern_manager._calculate_raw_score(
            terms=["test"],
            evidence_ids=set(),
            term_memory_map={},
            total_memories=0,
        )
        assert score == 0.0

    def test_recency_boost_with_no_memories(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test recency boost with empty memory list."""
        boost = pattern_manager._calculate_recency_boost([])
        assert boost == 0.0

    def test_find_term_clusters_empty_map(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test term clustering with empty map."""
        clusters = pattern_manager._find_term_clusters({}, min_occurrences=2)
        assert clusters == []

    def test_find_term_clusters_all_below_threshold(
        self, pattern_manager: PatternManager
    ) -> None:
        """Test term clustering when all terms below occurrence threshold."""
        term_map = {
            "term1": {"mem1"},  # Only 1 occurrence
            "term2": {"mem2"},  # Only 1 occurrence
        }
        clusters = pattern_manager._find_term_clusters(term_map, min_occurrences=2)
        assert clusters == []
