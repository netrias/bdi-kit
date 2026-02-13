"""CDE candidate serialization and prompt construction. Changes when the prompt format changes."""

from cde_recommend.types import CDE


def serialize_cde_candidates(cdes: list[CDE], *, max_pv_samples: int = 12) -> list[str]:
    out: list[str] = []
    for c in cdes:
        pv_count = len(c.pv_values)
        pv_samples = list(c.pv_values[:max_pv_samples])
        more = pv_count - len(pv_samples)
        if more > 0:
            pv_samples.append(f"...(+{more} more)")
        entry = f"CDE: {c.cde_key} (id={c.cde_id}), PV_count={pv_count}, PV_samples={pv_samples}"
        out.append(entry)
    return out


def build_developer_message(candidates_serialized: list[str], top_k: int) -> str:
    """Stable CDE context — cached by OpenAI across all columns in a batch."""
    list_block = "\n".join(f"{i}: {s}" for i, s in enumerate(candidates_serialized))
    return f"""You are an expert in schema matching.

Goal:
Given a SOURCE column (header + sample values), choose the best matching
TARGET CDE(s) from the candidate list.
A good match is semantically aligned AND compatible with the value space (e.g., PV samples).

Rules:
- Return up to {top_k} closest matches.
- Rank strictly from 1 (best) to {top_k}.
- If nothing fits, return exactly one item with candidate_index -1 and rank 0.
- IMPORTANT: Return indices only (candidate_index). Do NOT output strings.
- Output must be strict JSON matching the provided schema. No commentary.

TARGET CANDIDATES (index: CDE summary):
{list_block}"""


def build_user_message(source_column_serialized: str) -> str:
    """Varying suffix — changes per column."""
    return f"SOURCE:\n{source_column_serialized}"
