"""Tests for git_notes_memory.search module.

This module tests the SearchOptimizer and its components:
- SearchQuery and RankedResult data models
- SearchCache with LRU eviction and TTL expiration
- QueryExpander for synonym expansion
- ResultReranker for multi-signal ranking
- SearchOptimizer coordinator
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from git_notes_memory.models import Memory, MemoryResult
from git_notes_memory.search import (
    QueryExpander,
    RankedResult,
    ResultReranker,
    SearchCache,
    SearchOptimizer,
    SearchQuery,
    get_optimizer,
    reset_optimizer,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# Fixtures
# =============================================================================


def _make_memory_result(
    id: str,
    namespace: str,
    summary: str,
    distance: float,
    timestamp: datetime,
    spec: str | None = None,
    tags: tuple[str, ...] = (),
) -> MemoryResult:
    """Helper to create a MemoryResult wrapping a Memory."""
    memory = Memory(
        id=id,
        commit_sha=id.split(":")[1],
        namespace=namespace,
        summary=summary,
        content=f"Full content for: {summary}",
        timestamp=timestamp,
        spec=spec,
        tags=tags,
    )
    return MemoryResult(memory=memory, distance=distance)


@pytest.fixture
def sample_memory_result() -> MemoryResult:
    """Create a sample MemoryResult for testing."""
    return _make_memory_result(
        id="decisions:abc123:0",
        namespace="decisions",
        summary="Chose PostgreSQL for persistence",
        distance=0.25,
        timestamp=datetime.now(UTC),
        spec="project-alpha",
        tags=("database", "architecture"),
    )


@pytest.fixture
def sample_results_list() -> list[MemoryResult]:
    """Create a list of sample MemoryResults with varying attributes."""
    now = datetime.now(UTC)
    return [
        _make_memory_result(
            id="decisions:abc123:0",
            namespace="decisions",
            summary="Chose PostgreSQL for persistence",
            distance=0.25,
            timestamp=now,
            spec="project-alpha",
            tags=("database", "architecture"),
        ),
        _make_memory_result(
            id="learnings:def456:0",
            namespace="learnings",
            summary="SQLite works great for single-user apps",
            distance=0.30,
            timestamp=now - timedelta(days=7),
            spec="project-beta",
            tags=("database", "sqlite"),
        ),
        _make_memory_result(
            id="blockers:ghi789:0",
            namespace="blockers",
            summary="Connection pooling issue with high concurrency",
            distance=0.20,
            timestamp=now - timedelta(days=30),
            spec="project-alpha",
            tags=("database", "performance"),
        ),
        _make_memory_result(
            id="progress:jkl012:0",
            namespace="progress",
            summary="Implemented user authentication",
            distance=0.35,
            timestamp=now - timedelta(days=60),
            spec="project-gamma",
            tags=("auth", "security"),
        ),
    ]


# =============================================================================
# SearchQuery Tests
# =============================================================================


class TestSearchQuery:
    """Tests for SearchQuery data class."""

    def test_basic_creation(self) -> None:
        """Test basic SearchQuery creation."""
        query = SearchQuery(original="database decision")
        assert query.original == "database decision"
        assert query.expanded_terms == ()
        assert query.filters == {}

    def test_with_expanded_terms(self) -> None:
        """Test SearchQuery with expanded terms."""
        query = SearchQuery(
            original="database decision",
            expanded_terms=("db", "postgres", "chose"),
        )
        assert query.original == "database decision"
        assert query.expanded_terms == ("db", "postgres", "chose")

    def test_with_filters(self) -> None:
        """Test SearchQuery with filters."""
        query = SearchQuery(
            original="test",
            filters={"namespace": "decisions", "limit": 10},
        )
        assert query.filters["namespace"] == "decisions"
        assert query.filters["limit"] == 10

    def test_cache_key_deterministic(self) -> None:
        """Test that cache_key is deterministic for same inputs."""
        query1 = SearchQuery(
            original="test query",
            expanded_terms=("a", "b", "c"),
            filters={"namespace": "decisions"},
        )
        query2 = SearchQuery(
            original="test query",
            expanded_terms=("a", "b", "c"),
            filters={"namespace": "decisions"},
        )
        assert query1.cache_key() == query2.cache_key()

    def test_cache_key_different_for_different_queries(self) -> None:
        """Test that cache_key differs for different queries."""
        query1 = SearchQuery(original="test query 1")
        query2 = SearchQuery(original="test query 2")
        assert query1.cache_key() != query2.cache_key()

    def test_cache_key_different_for_different_expansions(self) -> None:
        """Test that cache_key differs for different expansions."""
        query1 = SearchQuery(original="test", expanded_terms=("a",))
        query2 = SearchQuery(original="test", expanded_terms=("b",))
        assert query1.cache_key() != query2.cache_key()

    def test_cache_key_length(self) -> None:
        """Test that cache_key is 16 characters (truncated SHA-256)."""
        query = SearchQuery(original="any query")
        assert len(query.cache_key()) == 16

    def test_cache_key_is_hex(self) -> None:
        """Test that cache_key is a valid hex string."""
        query = SearchQuery(original="any query")
        # Should not raise - all chars are hex
        int(query.cache_key(), 16)

    def test_frozen_dataclass(self) -> None:
        """Test that SearchQuery is immutable."""
        query = SearchQuery(original="test")
        with pytest.raises(AttributeError):
            query.original = "modified"  # type: ignore[misc]


# =============================================================================
# RankedResult Tests
# =============================================================================


class TestRankedResult:
    """Tests for RankedResult data class."""

    def test_basic_creation(self, sample_memory_result: MemoryResult) -> None:
        """Test basic RankedResult creation."""
        ranked = RankedResult(
            result=sample_memory_result,
            original_score=0.25,
            boosted_score=0.20,
        )
        assert ranked.result == sample_memory_result
        assert ranked.original_score == 0.25
        assert ranked.boosted_score == 0.20
        assert ranked.rank_factors == {}

    def test_with_rank_factors(self, sample_memory_result: MemoryResult) -> None:
        """Test RankedResult with rank factors."""
        ranked = RankedResult(
            result=sample_memory_result,
            original_score=0.25,
            boosted_score=0.18,
            rank_factors={"recency": 0.9, "namespace": 1.0, "spec": 0.5},
        )
        assert ranked.rank_factors["recency"] == 0.9
        assert ranked.rank_factors["namespace"] == 1.0

    def test_final_score_property(self, sample_memory_result: MemoryResult) -> None:
        """Test that final_score returns boosted_score."""
        ranked = RankedResult(
            result=sample_memory_result,
            original_score=0.25,
            boosted_score=0.15,
        )
        assert ranked.final_score == 0.15


# =============================================================================
# SearchCache Tests
# =============================================================================


class TestSearchCache:
    """Tests for SearchCache class."""

    def test_basic_get_set(self, sample_memory_result: MemoryResult) -> None:
        """Test basic cache get and set operations."""
        cache = SearchCache()
        results = [sample_memory_result]
        cache.set("key1", results)
        cached = cache.get("key1")
        assert cached is not None
        assert len(cached) == 1
        assert cached[0].id == sample_memory_result.id

    def test_get_missing_key(self) -> None:
        """Test getting a non-existent key returns None."""
        cache = SearchCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiration(self, sample_memory_result: MemoryResult) -> None:
        """Test that cache entries expire after TTL."""
        cache = SearchCache(_ttl_seconds=0.1)  # 100ms TTL
        results = [sample_memory_result]
        cache.set("key1", results)

        # Should be available immediately
        assert cache.get("key1") is not None

        # Wait for expiration
        time.sleep(0.15)

        # Should be expired now
        assert cache.get("key1") is None

    def test_lru_eviction(self, sample_memory_result: MemoryResult) -> None:
        """Test LRU eviction when cache is full."""
        cache = SearchCache(_max_size=3, _ttl_seconds=3600.0)
        results = [sample_memory_result]

        # Fill cache
        cache.set("key1", results)
        cache.set("key2", results)
        cache.set("key3", results)

        # Access key1 to make it recently used
        cache.get("key1")

        # Add key4 - should evict key2 (oldest not recently accessed)
        cache.set("key4", results)

        # key1 should still exist (was accessed)
        assert cache.get("key1") is not None
        # key2 should be evicted (oldest)
        assert cache.get("key2") is None
        # key3 and key4 should exist
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None

    def test_update_existing_key(self, sample_memory_result: MemoryResult) -> None:
        """Test updating an existing cache entry."""
        cache = SearchCache()
        cache.set("key1", [sample_memory_result])

        # Create a different result
        new_result = _make_memory_result(
            id="new:id:0",
            namespace="learnings",
            summary="New result",
            distance=0.5,
            timestamp=datetime.now(UTC),
        )
        cache.set("key1", [new_result])

        cached = cache.get("key1")
        assert cached is not None
        assert cached[0].id == "new:id:0"

    def test_invalidate_all(self, sample_memory_result: MemoryResult) -> None:
        """Test invalidating all cache entries."""
        cache = SearchCache()
        results = [sample_memory_result]
        cache.set("key1", results)
        cache.set("key2", results)
        cache.set("key3", results)

        count = cache.invalidate()
        assert count == 3
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_invalidate_with_pattern(self, sample_memory_result: MemoryResult) -> None:
        """Test invalidating cache entries matching a pattern."""
        cache = SearchCache()
        results = [sample_memory_result]
        cache.set("decisions:query1", results)
        cache.set("decisions:query2", results)
        cache.set("learnings:query3", results)

        count = cache.invalidate("decisions")
        assert count == 2
        assert cache.get("decisions:query1") is None
        assert cache.get("decisions:query2") is None
        assert cache.get("learnings:query3") is not None

    def test_stats(self, sample_memory_result: MemoryResult) -> None:
        """Test cache statistics."""
        cache = SearchCache(_max_size=50, _ttl_seconds=120.0)
        cache.set("key1", [sample_memory_result])
        cache.set("key2", [sample_memory_result])

        stats = cache.stats()
        assert stats["size"] == 2
        assert stats["max_size"] == 50
        assert stats["ttl_seconds"] == 120.0

    def test_empty_results_cacheable(self) -> None:
        """Test that empty results can be cached."""
        cache = SearchCache()
        cache.set("empty_query", [])
        cached = cache.get("empty_query")
        assert cached is not None
        assert len(cached) == 0


# =============================================================================
# QueryExpander Tests
# =============================================================================


class TestQueryExpander:
    """Tests for QueryExpander class."""

    def test_basic_expansion(self) -> None:
        """Test basic query expansion with synonyms."""
        expander = QueryExpander()
        query = expander.expand("database decision")

        assert query.original == "database decision"
        # Should have expansions for both "database" and "decision"
        assert len(query.expanded_terms) > 0
        # "db" is a synonym for "database"
        assert "db" in query.expanded_terms or "chose" in query.expanded_terms

    def test_no_expansion_for_unknown_terms(self) -> None:
        """Test that unknown terms don't get expanded."""
        expander = QueryExpander()
        query = expander.expand("xyzzy foobar")

        assert query.original == "xyzzy foobar"
        assert len(query.expanded_terms) == 0

    def test_domain_expansions(self) -> None:
        """Test domain-specific expansions."""
        expander = QueryExpander()
        query = expander.expand("frontend")

        assert query.original == "frontend"
        # Should have domain expansions like "react", "vue", etc.
        domain_terms = {"react", "vue", "angular", "ui", "client"}
        assert any(term in query.expanded_terms for term in domain_terms)

    def test_custom_synonyms(self) -> None:
        """Test using custom synonym dictionary."""
        custom_synonyms = {
            "foo": ["bar", "baz"],
            "hello": ["world", "hi"],
        }
        expander = QueryExpander(synonyms=custom_synonyms, domain_expansions={})
        query = expander.expand("foo hello")

        # Should use custom synonyms
        assert "bar" in query.expanded_terms or "baz" in query.expanded_terms
        assert "world" in query.expanded_terms or "hi" in query.expanded_terms

    def test_max_expansions_limit(self) -> None:
        """Test that max_expansions limits total expansions."""
        expander = QueryExpander(max_expansions=2)
        query = expander.expand("database decision problem")

        # Should be limited to max_expansions * 2 = 4 terms
        assert len(query.expanded_terms) <= 4

    def test_removes_original_terms(self) -> None:
        """Test that original query terms are not in expansions."""
        expander = QueryExpander()
        query = expander.expand("database")

        # "database" should not be in expanded terms
        assert "database" not in query.expanded_terms

    def test_tokenization_punctuation(self) -> None:
        """Test that punctuation is handled correctly."""
        expander = QueryExpander()
        query = expander.expand("why? database, decision!")

        assert query.original == "why? database, decision!"
        # Should expand "why", "database", and "decision"
        assert len(query.expanded_terms) > 0

    def test_with_filters(self) -> None:
        """Test expansion with filters."""
        expander = QueryExpander()
        query = expander.expand("database", filters={"namespace": "decisions"})

        assert query.filters == {"namespace": "decisions"}

    def test_single_char_tokens_ignored(self) -> None:
        """Test that single-character tokens are ignored."""
        expander = QueryExpander()
        query = expander.expand("a b c database")

        # Only "database" should trigger expansions
        # Single chars should not affect results
        assert "db" in query.expanded_terms or "postgres" in query.expanded_terms

    def test_empty_query(self) -> None:
        """Test expansion of empty query."""
        expander = QueryExpander()
        query = expander.expand("")

        assert query.original == ""
        assert len(query.expanded_terms) == 0


# =============================================================================
# ResultReranker Tests
# =============================================================================


class TestResultReranker:
    """Tests for ResultReranker class."""

    def test_basic_reranking(self, sample_results_list: list[MemoryResult]) -> None:
        """Test basic result re-ranking."""
        reranker = ResultReranker()
        query = SearchQuery(original="database")
        ranked = reranker.rerank(sample_results_list, query)

        assert len(ranked) == len(sample_results_list)
        # All results should have rank factors
        for r in ranked:
            assert "recency" in r.rank_factors
            assert "namespace" in r.rank_factors
            assert "spec" in r.rank_factors
            assert "tags" in r.rank_factors

    def test_recency_boosting(self) -> None:
        """Test that recent memories get boosted."""
        reranker = ResultReranker(recency_weight=0.5)
        now = datetime.now(UTC)

        recent = _make_memory_result(
            id="recent:rec1:0",
            namespace="decisions",
            summary="Recent",
            distance=0.30,
            timestamp=now,
        )
        old = _make_memory_result(
            id="old:old1:0",
            namespace="decisions",
            summary="Old",
            distance=0.30,
            timestamp=now - timedelta(days=180),
        )

        query = SearchQuery(original="test")
        ranked = reranker.rerank([old, recent], query)

        # Recent should have higher recency factor
        recent_ranked = next(r for r in ranked if r.result.id == "recent:rec1:0")
        old_ranked = next(r for r in ranked if r.result.id == "old:old1:0")

        assert (
            recent_ranked.rank_factors["recency"] > old_ranked.rank_factors["recency"]
        )

    def test_namespace_priority(self) -> None:
        """Test namespace priority boosting."""
        reranker = ResultReranker(namespace_weight=0.5)
        now = datetime.now(UTC)

        decisions = _make_memory_result(
            id="decisions:dec1:0",
            namespace="decisions",
            summary="Decision",
            distance=0.30,
            timestamp=now,
        )
        progress = _make_memory_result(
            id="progress:prg1:0",
            namespace="progress",
            summary="Progress",
            distance=0.30,
            timestamp=now,
        )

        query = SearchQuery(original="test")
        ranked = reranker.rerank([progress, decisions], query)

        # Decisions namespace should have higher priority
        decisions_ranked = next(r for r in ranked if r.result.id == "decisions:dec1:0")
        progress_ranked = next(r for r in ranked if r.result.id == "progress:prg1:0")

        assert (
            decisions_ranked.rank_factors["namespace"]
            > progress_ranked.rank_factors["namespace"]
        )

    def test_spec_matching(self, sample_results_list: list[MemoryResult]) -> None:
        """Test spec matching boosting."""
        reranker = ResultReranker(spec_weight=0.5)
        query = SearchQuery(original="database")
        ranked = reranker.rerank(
            sample_results_list, query, target_spec="project-alpha"
        )

        # Results from project-alpha should have spec boost
        for r in ranked:
            if r.result.spec == "project-alpha":
                assert r.rank_factors["spec"] == 1.0
            else:
                assert r.rank_factors["spec"] == 0.0

    def test_tag_matching(self, sample_results_list: list[MemoryResult]) -> None:
        """Test tag matching boosting."""
        reranker = ResultReranker(tag_weight=0.5)
        query = SearchQuery(original="database")
        ranked = reranker.rerank(
            sample_results_list, query, target_tags=["database", "architecture"]
        )

        # Results with matching tags should have tag boost
        for r in ranked:
            if r.result.tags and "database" in r.result.tags:
                assert r.rank_factors["tags"] > 0

    def test_target_namespace_extra_boost(self) -> None:
        """Test extra boost for target namespace match."""
        reranker = ResultReranker(namespace_weight=0.5)
        now = datetime.now(UTC)

        result = _make_memory_result(
            id="decisions:dec1:0",
            namespace="decisions",
            summary="Decision",
            distance=0.30,
            timestamp=now,
        )

        query = SearchQuery(original="test")

        # Without target namespace
        ranked_no_target = reranker.rerank([result], query)
        # With target namespace matching
        ranked_with_target = reranker.rerank(
            [result], query, target_namespace="decisions"
        )

        # Should get extra boost when target namespace matches
        assert (
            ranked_with_target[0].rank_factors["namespace"]
            > ranked_no_target[0].rank_factors["namespace"]
        )

    def test_score_boosting_improves_ranking(self) -> None:
        """Test that boosting actually improves ranking of relevant results.

        This test verifies that when raw vector scores are close, the boosting
        signals (recency, namespace priority, spec/tag matching) can flip the
        ranking to prioritize more contextually relevant results.
        """
        reranker = ResultReranker()
        now = datetime.now(UTC)

        # Create results where raw scores are close enough that boosting matters
        # The boost reduces the effective distance, so high-boost items rank first
        good_match = _make_memory_result(
            id="good:goo1:0",
            namespace="decisions",  # High priority namespace (1.0)
            summary="Relevant decision",
            distance=0.30,  # Slightly worse raw score
            timestamp=now,  # Very recent (recency ~1.0)
            spec="target-spec",  # Matches target (spec=1.0)
            tags=("relevant",),  # Matches target (tags=1.0)
        )
        poor_match = _make_memory_result(
            id="poor:poo1:0",
            namespace="progress",  # Lower priority namespace (0.7)
            summary="Some progress",
            distance=0.28,  # Slightly better raw score
            timestamp=now - timedelta(days=90),  # Old (low recency)
            spec="other-spec",  # No spec match
            tags=("unrelated",),  # No tag match
        )

        query = SearchQuery(original="test")
        ranked = reranker.rerank(
            [poor_match, good_match],
            query,
            target_spec="target-spec",
            target_tags=["relevant"],
        )

        # After boosting, good_match should rank first because it has:
        # - Higher recency boost (~1.0 vs ~0.2)
        # - Higher namespace priority (1.0 vs 0.7)
        # - Spec match (1.0 vs 0.0)
        # - Tag match (1.0 vs 0.0)
        # Total boost for good_match > poor_match, overcoming 0.02 distance diff
        assert ranked[0].result.id == "good:goo1:0"

    def test_boosted_score_non_negative(
        self, sample_results_list: list[MemoryResult]
    ) -> None:
        """Test that boosted scores are never negative."""
        reranker = ResultReranker(
            recency_weight=1.0,
            namespace_weight=1.0,
            spec_weight=1.0,
            tag_weight=1.0,
        )
        query = SearchQuery(original="test")
        ranked = reranker.rerank(sample_results_list, query)

        for r in ranked:
            assert r.boosted_score >= 0.0

    def test_empty_results(self) -> None:
        """Test re-ranking empty results."""
        reranker = ResultReranker()
        query = SearchQuery(original="test")
        ranked = reranker.rerank([], query)

        assert ranked == []

    def test_results_sorted_by_boosted_score(
        self, sample_results_list: list[MemoryResult]
    ) -> None:
        """Test that results are sorted by boosted score (ascending)."""
        reranker = ResultReranker()
        query = SearchQuery(original="database")
        ranked = reranker.rerank(sample_results_list, query)

        # Verify sorted order (lower boosted score = better rank)
        for i in range(len(ranked) - 1):
            assert ranked[i].boosted_score <= ranked[i + 1].boosted_score


# =============================================================================
# SearchOptimizer Tests
# =============================================================================


class TestSearchOptimizer:
    """Tests for SearchOptimizer coordinator class."""

    def test_default_initialization(self) -> None:
        """Test default initialization creates all components."""
        optimizer = SearchOptimizer()
        assert optimizer.expander is not None
        assert optimizer.reranker is not None
        assert optimizer.cache is not None

    def test_custom_components(self) -> None:
        """Test initialization with custom components."""
        expander = QueryExpander(max_expansions=3)
        reranker = ResultReranker(recency_weight=0.5)
        cache = SearchCache(_max_size=50)

        optimizer = SearchOptimizer(expander=expander, reranker=reranker, cache=cache)

        assert optimizer.expander is expander
        assert optimizer.reranker is reranker
        assert optimizer.cache is cache

    def test_expand_query(self) -> None:
        """Test query expansion through optimizer."""
        optimizer = SearchOptimizer()
        query = optimizer.expand_query("database decision")

        assert isinstance(query, SearchQuery)
        assert query.original == "database decision"
        assert len(query.expanded_terms) > 0

    def test_expand_query_with_filters(self) -> None:
        """Test query expansion with filters."""
        optimizer = SearchOptimizer()
        query = optimizer.expand_query(
            "database",
            filters={"namespace": "decisions", "limit": 5},
        )

        assert query.filters["namespace"] == "decisions"
        assert query.filters["limit"] == 5

    def test_rerank_results(self, sample_results_list: list[MemoryResult]) -> None:
        """Test result re-ranking through optimizer."""
        optimizer = SearchOptimizer()
        query = optimizer.expand_query("database")
        ranked = optimizer.rerank_results(sample_results_list, query)

        assert len(ranked) == len(sample_results_list)
        assert all(isinstance(r, RankedResult) for r in ranked)

    def test_cache_integration(self, sample_memory_result: MemoryResult) -> None:
        """Test cache operations through optimizer."""
        optimizer = SearchOptimizer()
        results = [sample_memory_result]

        # Cache should be empty
        assert optimizer.get_cached("test_key") is None

        # Set cache
        optimizer.cache_results("test_key", results)

        # Should retrieve from cache
        cached = optimizer.get_cached("test_key")
        assert cached is not None
        assert cached[0].id == sample_memory_result.id

    def test_invalidate_cache(self, sample_memory_result: MemoryResult) -> None:
        """Test cache invalidation through optimizer."""
        optimizer = SearchOptimizer()
        results = [sample_memory_result]

        optimizer.cache_results("key1", results)
        optimizer.cache_results("key2", results)

        count = optimizer.invalidate_cache()
        assert count == 2
        assert optimizer.get_cached("key1") is None
        assert optimizer.get_cached("key2") is None

    def test_cache_stats(self, sample_memory_result: MemoryResult) -> None:
        """Test cache statistics through optimizer."""
        optimizer = SearchOptimizer()
        optimizer.cache_results("key1", [sample_memory_result])

        stats = optimizer.cache_stats()
        assert stats["size"] == 1
        assert "max_size" in stats
        assert "ttl_seconds" in stats

    def test_full_workflow(self, sample_results_list: list[MemoryResult]) -> None:
        """Test complete search optimization workflow."""
        optimizer = SearchOptimizer()

        # 1. Expand query
        query = optimizer.expand_query("database decision")

        # 2. Check cache (miss expected)
        cache_key = query.cache_key()
        cached = optimizer.get_cached(cache_key)
        assert cached is None

        # 3. Re-rank results
        ranked = optimizer.rerank_results(
            sample_results_list,
            query,
            target_spec="project-alpha",
            target_tags=["database"],
        )

        # 4. Cache results
        final_results = [r.result for r in ranked]
        optimizer.cache_results(cache_key, final_results)

        # 5. Verify cache hit
        cached = optimizer.get_cached(cache_key)
        assert cached is not None
        assert len(cached) == len(sample_results_list)


# =============================================================================
# Module Singleton Tests
# =============================================================================


class TestModuleSingleton:
    """Tests for module-level singleton functions."""

    def test_get_optimizer_returns_instance(self) -> None:
        """Test that get_optimizer returns a SearchOptimizer instance."""
        optimizer = get_optimizer()
        assert isinstance(optimizer, SearchOptimizer)

    def test_get_optimizer_returns_same_instance(self) -> None:
        """Test that get_optimizer returns the same singleton instance."""
        optimizer1 = get_optimizer()
        optimizer2 = get_optimizer()
        assert optimizer1 is optimizer2

    def test_reset_optimizer(self) -> None:
        """Test that reset_optimizer clears the singleton."""
        optimizer1 = get_optimizer()
        reset_optimizer()
        optimizer2 = get_optimizer()
        assert optimizer1 is not optimizer2


# =============================================================================
# Integration Tests
# =============================================================================


class TestSearchIntegration:
    """Integration tests for search optimization."""

    def test_expansion_improves_recall_concept(self) -> None:
        """Test that query expansion conceptually improves recall.

        This test verifies that expanded terms are semantically related
        to the original query, which should improve recall in real searches.
        """
        expander = QueryExpander()

        # Decision-related query
        query = expander.expand("why decided")
        expected_expansions = {"reason", "rationale", "chose", "selected", "decision"}
        assert any(term in query.expanded_terms for term in expected_expansions)

        # Problem-related query
        query = expander.expand("bug error")
        expected_expansions = {"problem", "issue", "defect", "failure"}
        assert any(term in query.expanded_terms for term in expected_expansions)

    def test_reranking_with_real_temporal_decay(self) -> None:
        """Test re-ranking with actual temporal decay calculation."""
        reranker = ResultReranker()
        now = datetime.now(UTC)

        # Create results at different ages
        results = [
            _make_memory_result(
                id=f"result:res{i}:0",
                namespace="decisions",
                summary=f"Result {i}",
                distance=0.3,  # Same raw score
                timestamp=now - timedelta(days=i * 30),  # 0, 30, 60, 90 days
            )
            for i in range(4)
        ]

        query = SearchQuery(original="test")
        ranked = reranker.rerank(results, query)

        # Recency factors should decrease with age
        recency_factors = [r.rank_factors["recency"] for r in ranked]
        # Note: ranked is sorted by boosted_score, not original order
        # So we check that the most recent has highest recency
        most_recent = next(r for r in ranked if "result:res0" in r.result.id)
        oldest = next(r for r in ranked if "result:res3" in r.result.id)
        assert most_recent.rank_factors["recency"] > oldest.rank_factors["recency"]

    def test_optimizer_handles_old_timestamps(self) -> None:
        """Test that optimizer handles memories with very old timestamps."""
        reranker = ResultReranker()

        # Very old timestamp (1 year ago) should have near-zero recency boost
        old_timestamp = datetime.now(UTC) - timedelta(days=365)
        result = _make_memory_result(
            id="old_time:old1:0",
            namespace="decisions",
            summary="Very old memory",
            distance=0.3,
            timestamp=old_timestamp,
        )

        query = SearchQuery(original="test")
        ranked = reranker.rerank([result], query)

        # Should handle gracefully - recency should be low for old timestamp
        assert len(ranked) == 1
        # Temporal decay should be very low for 1-year-old memory
        assert ranked[0].rank_factors["recency"] < 0.1

    def test_optimizer_handles_empty_tags(self) -> None:
        """Test that optimizer handles memories without tags (empty tuple)."""
        reranker = ResultReranker()

        # Memory with empty tags (the default)
        result = _make_memory_result(
            id="no_tags:ntg1:0",
            namespace="decisions",
            summary="No tags",
            distance=0.3,
            timestamp=datetime.now(UTC),
            tags=(),  # Empty tuple
        )

        query = SearchQuery(original="test")
        ranked = reranker.rerank([result], query, target_tags=["database"])

        # Should handle gracefully - no tag matches means 0 tag boost
        assert len(ranked) == 1
        assert ranked[0].rank_factors["tags"] == 0.0


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_query(self) -> None:
        """Test handling of very long queries."""
        expander = QueryExpander()
        long_query = " ".join(["database"] * 100)
        query = expander.expand(long_query)

        # Should not crash and should limit expansions
        assert query.original == long_query
        assert len(query.expanded_terms) <= 10  # max_expansions * 2

    def test_special_characters_in_query(self) -> None:
        """Test handling of special characters."""
        expander = QueryExpander()
        query = expander.expand("database@#$%^&* decision!!!")

        # Should extract meaningful tokens
        assert query.original == "database@#$%^&* decision!!!"
        # Should still expand "database" and "decision"
        assert len(query.expanded_terms) > 0

    def test_unicode_in_query(self) -> None:
        """Test handling of unicode characters."""
        expander = QueryExpander()
        query = expander.expand("database 数据库 décision")

        # Should not crash
        assert query.original == "database 数据库 décision"

    def test_cache_with_very_large_results(self) -> None:
        """Test cache with large result sets."""
        cache = SearchCache()
        now = datetime.now(UTC)
        results = [
            _make_memory_result(
                id=f"result:res{i:04d}:0",
                namespace="decisions",
                summary=f"Result {i}",
                distance=0.3,
                timestamp=now,
            )
            for i in range(1000)
        ]

        cache.set("large_key", results)
        cached = cache.get("large_key")

        assert cached is not None
        assert len(cached) == 1000

    def test_rerank_preserves_result_data(
        self, sample_results_list: list[MemoryResult]
    ) -> None:
        """Test that re-ranking preserves all result data."""
        reranker = ResultReranker()
        query = SearchQuery(original="test")
        ranked = reranker.rerank(sample_results_list, query)

        # Verify all original result data is preserved
        original_ids = {r.id for r in sample_results_list}
        ranked_ids = {r.result.id for r in ranked}
        assert original_ids == ranked_ids

    def test_concurrent_cache_access_safety(
        self, sample_memory_result: MemoryResult
    ) -> None:
        """Test that cache operations are safe for sequential access.

        Note: This is a basic safety check. For true concurrency testing,
        threading tests would be needed.
        """
        cache = SearchCache(_max_size=5)
        results = [sample_memory_result]

        # Simulate rapid sequential access
        for i in range(100):
            cache.set(f"key_{i}", results)
            if i > 0:
                # Old keys should be evicted once we exceed max_size
                pass

        # Cache should maintain max_size constraint
        assert cache.stats()["size"] <= 5
