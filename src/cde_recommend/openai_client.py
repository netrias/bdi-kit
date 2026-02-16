"""AsyncOpenAI client wrapper with structured-output calls. Changes when OpenAI API evolves."""

import json
import os

from openai import AsyncOpenAI

from cde_recommend.schema import TEXT_FORMAT_CONFIG
from cde_recommend.types import PotentialMatchIndex, UsageStats

_client_singleton: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Lazy singleton — reused across Lambda warm starts."""
    global _client_singleton  # noqa: PLW0603
    if _client_singleton is None:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("Missing OPENAI_API_KEY env var.")
        _client_singleton = AsyncOpenAI(api_key=key)
    return _client_singleton


async def call_rank_indices(
    client: AsyncOpenAI,
    model: str,
    developer_message: str,
    user_message: str,
    effort: str = "minimal",
) -> tuple[list[PotentialMatchIndex], UsageStats]:
    """Developer message (CDEs) is the cached prefix; user message (column) varies."""
    resp = await client.responses.create(
        model=model,
        input=[
            {"role": "developer", "content": developer_message},
            {"role": "user", "content": user_message},
        ],
        text=TEXT_FORMAT_CONFIG,  # type: ignore[arg-type]
        reasoning={"effort": effort},  # type: ignore[arg-type]
        store=False,
    )
    data = json.loads(resp.output_text)

    raw_matches = data.get("closest_matches") or []
    matches = [PotentialMatchIndex.model_validate(m) for m in raw_matches]

    usage = UsageStats(
        input_tokens=getattr(resp.usage, "input_tokens", 0) or 0,
        output_tokens=getattr(resp.usage, "output_tokens", 0) or 0,
        total_tokens=getattr(resp.usage, "total_tokens", 0) or 0,
    )
    return matches, usage
