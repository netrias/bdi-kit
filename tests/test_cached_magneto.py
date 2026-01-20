"""Tests for CachedMagnetoFTBP matcher.

These tests require downloading large models and are marked as slow.
Run with: pytest tests/test_cached_magneto.py -v
Skip slow tests with: pytest tests/test_cached_magneto.py -v -m "not slow"
"""

import pandas as pd
import pytest
import torch

from bdikit.schema_matching.cached_magneto import (
    CachedMagnetoFTBP,
    EmbeddingCache,
)


@pytest.fixture
def sample_source_df() -> pd.DataFrame:
    """Sample source DataFrame for testing."""
    return pd.DataFrame({
        "age": ["25", "30", "45"],
        "sex": ["male", "female", "male"],
        "race": ["white", "black", "asian"],
    })


@pytest.fixture
def sample_target_df() -> pd.DataFrame:
    """Sample target DataFrame for testing."""
    return pd.DataFrame({
        "age_at_diagnosis": ["0-17", "18-30", "31-45"],
        "biological_sex": ["male", "female", "unknown"],
        "ethnicity": ["hispanic", "non-hispanic", "unknown"],
        "sample_type": ["blood", "tissue", "saliva"],
    })


class TestEmbeddingCache:
    """Tests for EmbeddingCache dataclass."""

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        """Test serialization/deserialization roundtrip."""
        embeddings = torch.randn(5, 768)
        column_order = ["col1", "col2", "col3", "col4", "col5"]
        content_hash = "abc123"
        model_name = "test-model"
        encoding_mode = "header_values_verbose"

        cache = EmbeddingCache(
            embeddings=embeddings,
            column_order=column_order,
            content_hash=content_hash,
            model_name=model_name,
            encoding_mode=encoding_mode,
        )

        cache_dict = cache.to_dict()
        restored = EmbeddingCache.from_dict(cache_dict)

        assert torch.equal(restored.embeddings, embeddings)
        assert restored.column_order == column_order
        assert restored.content_hash == content_hash
        assert restored.model_name == model_name
        assert restored.encoding_mode == encoding_mode


class TestCacheValidation:
    """Tests for cache validation logic (no model loading required)."""

    def test_model_name_mismatch_raises_error(
        self, sample_source_df: pd.DataFrame, sample_target_df: pd.DataFrame
    ) -> None:
        """Test that mismatched model names raise ValueError."""
        cache = EmbeddingCache(
            embeddings=torch.randn(4, 768),
            column_order=["col1", "col2", "col3", "col4"],
            content_hash="test_hash",
            model_name="different-model",
            encoding_mode="header_values_verbose",
        )
        matcher = CachedMagnetoFTBP(
            cached_target=cache, model_name="magneto-gdc-v0.1"
        )
        with pytest.raises(ValueError, match="Cache model .* does not match"):
            matcher.rank_schema_matches(sample_source_df, sample_target_df, top_k=3)

    def test_encoding_mode_mismatch_raises_error(
        self, sample_source_df: pd.DataFrame, sample_target_df: pd.DataFrame
    ) -> None:
        """Test that mismatched encoding modes raise ValueError."""
        cache = EmbeddingCache(
            embeddings=torch.randn(4, 768),
            column_order=["col1", "col2", "col3", "col4"],
            content_hash="test_hash",
            model_name="magneto-gdc-v0.1",
            encoding_mode="different_encoding",
        )
        matcher = CachedMagnetoFTBP(
            cached_target=cache, encoding_mode="header_values_verbose"
        )
        with pytest.raises(ValueError, match="Cache encoding_mode .* does not match"):
            matcher.rank_schema_matches(sample_source_df, sample_target_df, top_k=3)


@pytest.mark.slow
class TestCachedMagnetoFTBP:
    """Tests for CachedMagnetoFTBP matcher.

    These tests download ML models and are slow.
    """

    def test_compute_target_embeddings(self, sample_target_df: pd.DataFrame):
        """Test pre-computing target embeddings."""
        cache = CachedMagnetoFTBP.compute_target_embeddings(
            target_df=sample_target_df,
            content_hash="test_hash_123",
        )

        assert cache.embeddings.shape[0] == len(sample_target_df.columns)
        assert cache.embeddings.shape[1] == 768  # mpnet embedding dim
        assert len(cache.column_order) == len(sample_target_df.columns)
        assert cache.content_hash == "test_hash_123"
        assert cache.model_name == "magneto-gdc-v0.1"

    def test_rank_schema_matches_without_cache(
        self, sample_source_df: pd.DataFrame, sample_target_df: pd.DataFrame
    ):
        """Test matching without cached embeddings (fresh computation)."""
        matcher = CachedMagnetoFTBP()
        matches = matcher.rank_schema_matches(
            source=sample_source_df,
            target=sample_target_df,
            top_k=3,
        )

        assert len(matches) > 0
        # Check that source columns are in the matches
        source_cols_matched = {m.source_column for m in matches}
        assert source_cols_matched.issubset(set(sample_source_df.columns))

    def test_rank_schema_matches_with_cache(
        self, sample_source_df: pd.DataFrame, sample_target_df: pd.DataFrame
    ):
        """Test matching with pre-computed cached embeddings."""
        # First compute cache
        cache = CachedMagnetoFTBP.compute_target_embeddings(
            target_df=sample_target_df,
            content_hash="test_hash_456",
        )

        # Then use cached matcher
        matcher = CachedMagnetoFTBP(cached_target=cache)
        matches = matcher.rank_schema_matches(
            source=sample_source_df,
            target=sample_target_df,
            top_k=3,
        )

        assert len(matches) > 0
        source_cols_matched = {m.source_column for m in matches}
        assert source_cols_matched.issubset(set(sample_source_df.columns))

    def test_cached_vs_uncached_produces_same_results(
        self, sample_source_df: pd.DataFrame, sample_target_df: pd.DataFrame
    ):
        """Test that cached and uncached matching produce identical results."""
        # Compute cache
        cache = CachedMagnetoFTBP.compute_target_embeddings(
            target_df=sample_target_df,
            content_hash="test_hash_789",
        )

        # Match without cache
        matcher_uncached = CachedMagnetoFTBP()
        matches_uncached = matcher_uncached.rank_schema_matches(
            source=sample_source_df,
            target=sample_target_df,
            top_k=3,
        )

        # Match with cache
        matcher_cached = CachedMagnetoFTBP(cached_target=cache)
        matches_cached = matcher_cached.rank_schema_matches(
            source=sample_source_df,
            target=sample_target_df,
            top_k=3,
        )

        # Results should be identical
        assert len(matches_uncached) == len(matches_cached)

        for m1, m2 in zip(matches_uncached, matches_cached):
            assert m1.source_column == m2.source_column
            assert m1.target_column == m2.target_column
            assert abs(m1.similarity - m2.similarity) < 1e-5

    def test_empty_source_returns_empty_matches(self, sample_target_df: pd.DataFrame):
        """Test that empty source DataFrame returns empty matches."""
        empty_source = pd.DataFrame()
        matcher = CachedMagnetoFTBP()
        matches = matcher.rank_schema_matches(
            source=empty_source,
            target=sample_target_df,
            top_k=3,
        )
        assert matches == []

    def test_empty_target_returns_empty_matches(self, sample_source_df: pd.DataFrame):
        """Test that empty target DataFrame returns empty matches."""
        empty_target = pd.DataFrame()
        matcher = CachedMagnetoFTBP()
        matches = matcher.rank_schema_matches(
            source=sample_source_df,
            target=empty_target,
            top_k=3,
        )
        assert matches == []
