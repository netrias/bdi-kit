"""CachedMagnetoFTBP: Magneto matcher with pre-computed target embeddings.

Axis of change: embedding computation strategy, caching format.
Constraint: cached embeddings must match the model and encoding mode used at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import torch
from magneto.bp_reranker import arrange_bipartite_matches
from magneto.column_encoder import ColumnEncoder
from magneto.utils.embedding_utils import compute_cosine_similarity_simple
from magneto.utils.utils import clean_df
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

from bdikit.download import get_cached_model_or_download
from bdikit.schema_matching.base import BaseTopkSchemaMatcher, ColumnMatch
from bdikit.schema_matching.magneto import DEFAULT_MAGNETO_MODEL

DEFAULT_ENCODING_MODE = "header_values_verbose"
DEFAULT_SAMPLING_MODE = "mixed"
DEFAULT_SAMPLING_SIZE = 10

_BASE_MODELS = {
    "mpnet": "sentence-transformers/all-mpnet-base-v2",
    "roberta": "sentence-transformers/all-roberta-large-v1",
    "minilm": "sentence-transformers/all-MiniLM-L6-v2",
}

_MODEL_CACHE: dict[str, tuple[SentenceTransformer, AutoTokenizer]] = {}


@dataclass
class EmbeddingCache:
    """Cached target embeddings for fast schema matching."""

    embeddings: torch.Tensor
    """Target column embeddings, shape [N, embedding_dim]."""

    column_order: list[str]
    """Column names in the order matching the embeddings tensor."""

    content_hash: str
    """Hash of schema + model + encoding for cache validation."""

    model_name: str
    """Model that generated these embeddings."""

    encoding_mode: str
    """Encoding mode used to generate text representations."""

    def to_dict(self) -> dict[str, Any]:
        """torch.Tensor won't JSON-serialize; use torch.save() on the returned dict."""
        return {
            "embeddings": self.embeddings,
            "column_order": self.column_order,
            "content_hash": self.content_hash,
            "model_name": self.model_name,
            "encoding_mode": self.encoding_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingCache:
        return cls(
            embeddings=data["embeddings"],
            column_order=data["column_order"],
            content_hash=data["content_hash"],
            model_name=data["model_name"],
            encoding_mode=data["encoding_mode"],
        )


class CachedMagnetoFTBP(BaseTopkSchemaMatcher):
    """Magneto matcher with support for pre-computed target embeddings.

    When cached_target is provided, only source column embeddings are computed
    at matching time. This dramatically reduces execution time for repeated
    matching against the same target schema.
    """

    def __init__(
        self,
        cached_target: EmbeddingCache | None = None,
        encoding_mode: str = DEFAULT_ENCODING_MODE,
        model_name: str = DEFAULT_MAGNETO_MODEL,
        sampling_mode: str = DEFAULT_SAMPLING_MODE,
        sampling_size: int = DEFAULT_SAMPLING_SIZE,
        embedding_threshold: float = 0.1,
    ):
        self.cached_target = cached_target
        self.encoding_mode = encoding_mode
        self.model_name = model_name
        self.sampling_mode = sampling_mode
        self.sampling_size = sampling_size
        self.embedding_threshold = embedding_threshold

        self._model: SentenceTransformer | None = None
        self._tokenizer: AutoTokenizer | None = None
        self._encoder: ColumnEncoder | None = None

    @classmethod
    def compute_target_embeddings(
        cls,
        target_df: pd.DataFrame,
        content_hash: str,
        model_name: str = DEFAULT_MAGNETO_MODEL,
        encoding_mode: str = DEFAULT_ENCODING_MODE,
        sampling_mode: str = DEFAULT_SAMPLING_MODE,
        sampling_size: int = DEFAULT_SAMPLING_SIZE,
    ) -> EmbeddingCache:
        """Pre-compute embeddings in Prepare Lambda; store in S3 for worker reuse."""
        matcher = cls(
            cached_target=None,
            encoding_mode=encoding_mode,
            model_name=model_name,
            sampling_mode=sampling_mode,
            sampling_size=sampling_size,
        )
        matcher._ensure_model_loaded()
        assert matcher._encoder is not None

        target_cleaned = clean_df(target_df)
        column_order = list(target_cleaned.columns)

        col_texts = [
            matcher._encoder.encode(target_cleaned, col) for col in column_order
        ]
        embeddings = matcher._get_embeddings(col_texts)

        return EmbeddingCache(
            embeddings=embeddings,
            column_order=column_order,
            content_hash=content_hash,
            model_name=model_name,
            encoding_mode=encoding_mode,
        )

    def rank_schema_matches(
        self, source: pd.DataFrame, target: pd.DataFrame, top_k: int
    ) -> list[ColumnMatch]:
        self._validate_cache()
        self._ensure_model_loaded()
        assert self._encoder is not None

        source_cleaned = clean_df(source)
        target_cleaned = clean_df(target)

        if len(source_cleaned.columns) == 0 or len(target_cleaned.columns) == 0:
            return []

        # List of tuples preserves column identity when two columns encode to identical text
        source_encoded = [
            (self._encoder.encode(source_cleaned, col), col)
            for col in source_cleaned.columns
        ]
        source_texts = [text for text, _ in source_encoded]
        source_embeddings = self._get_embeddings(source_texts)

        if self.cached_target is not None:
            target_embeddings = self.cached_target.embeddings.to(
                source_embeddings.device
            )
            target_columns = self.cached_target.column_order
        else:
            target_encoded = [
                (self._encoder.encode(target_cleaned, col), col)
                for col in target_cleaned.columns
            ]
            target_texts = [text for text, _ in target_encoded]
            target_embeddings = self._get_embeddings(target_texts)
            target_columns = [col for _, col in target_encoded]

        effective_top_k = min(top_k, len(target_columns))
        similarities, indices = compute_cosine_similarity_simple(
            source_embeddings, target_embeddings, effective_top_k
        )

        input_sim_map: dict[str, dict[str, float]] = {
            col: {} for col in source_cleaned.columns
        }

        for i, (_, source_col) in enumerate(source_encoded):
            for j in range(effective_top_k):
                target_idx = int(indices[i, j].item())
                similarity = float(similarities[i, j].item())
                if similarity >= self.embedding_threshold:
                    target_col = target_columns[target_idx]
                    input_sim_map[source_col][target_col] = similarity

        matches_valentine = _to_valentine_format(input_sim_map, "source", "target")
        if matches_valentine:
            matches_valentine = arrange_bipartite_matches(
                matches_valentine,
                source_cleaned,
                "source",
                target_cleaned,
                "target",
            )

        matches = []
        for (src_tuple, tgt_tuple), score in matches_valentine.items():
            source_col = src_tuple[1]
            target_col = tgt_tuple[1]
            matches.append(ColumnMatch(source_col, target_col, score))

        return self._sort_ranked_matches(matches)

    def _validate_cache(self) -> None:
        """Mismatched model/encoding produces silently wrong similarity scores."""
        if self.cached_target is None:
            return
        if self.cached_target.model_name != self.model_name:
            raise ValueError(
                f"Cache model '{self.cached_target.model_name}' does not match "
                f"matcher model '{self.model_name}'"
            )
        if self.cached_target.encoding_mode != self.encoding_mode:
            raise ValueError(
                f"Cache encoding_mode '{self.cached_target.encoding_mode}' does not "
                f"match matcher encoding_mode '{self.encoding_mode}'"
            )

    def _ensure_model_loaded(self) -> None:
        """Defer ~10s model load until matching is actually requested."""
        if self._model is None:
            self._model, self._tokenizer = _get_cached_model(self.model_name)
            self._encoder = ColumnEncoder(
                self._tokenizer,
                encoding_mode=self.encoding_mode,
                sampling_mode=self.sampling_mode,
                n_samples=self.sampling_size,
            )

    def _get_embeddings(self, texts: list[str], batch_size: int = 32) -> torch.Tensor:
        """Batch to avoid OOM on large column sets."""
        self._ensure_model_loaded()
        assert self._model is not None

        device_str = str(next(self._model.parameters()).device)
        embeddings: list[torch.Tensor] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            with torch.no_grad():
                embeds = self._model.encode(
                    batch,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                    device=device_str,
                )
            embeddings.append(embeds)  # type: ignore[arg-type]

        return torch.cat(embeddings)


def _get_cached_model(model_name: str) -> tuple[SentenceTransformer, AutoTokenizer]:
    """Model loading takes ~10s; cache survives Lambda warm starts."""
    if model_name not in _MODEL_CACHE:
        device_str = "cuda" if torch.cuda.is_available() else "cpu"

        base_key = next((k for k in _BASE_MODELS if k in model_name), "mpnet")
        base_model_path = _BASE_MODELS[base_key]

        model = SentenceTransformer(base_model_path, device=device_str)
        tokenizer = AutoTokenizer.from_pretrained(base_model_path)

        if model_name not in _BASE_MODELS:
            model_path = Path(get_cached_model_or_download(model_name))
            if model_path.exists():
                state_dict = torch.load(
                    model_path, map_location=device_str, weights_only=False
                )
                model.load_state_dict(state_dict)
                model.eval().to(device_str)

        _MODEL_CACHE[model_name] = (model, tokenizer)

    return _MODEL_CACHE[model_name]


def _to_valentine_format(
    sim_map: dict[str, dict[str, float]], source_name: str, target_name: str
) -> dict[tuple[tuple[str, str], tuple[str, str]], float]:
    """Valentine's bipartite reranker expects ((table, col), (table, col)) keys."""
    result = {}
    for source_col, targets in sim_map.items():
        for target_col, score in targets.items():
            key = ((source_name, source_col), (target_name, target_col))
            result[key] = score
    return result
