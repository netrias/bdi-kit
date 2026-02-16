# ADR 003: Filter High-Cardinality CDEs from Recommendations

## Status

Accepted (temporary measure)

## Context

Several CDEs have very large permissible-value (PV) sets that function as medical ontology fields rather than categorical fields:

- `treatment_agent`: 4,477 PVs
- `laboratory_test_name`: 1,055 PVs
- `adverse_event`: 790 PVs

The LLM-based matcher sends only 12 PV samples per CDE prompt. For high-cardinality CDEs, these samples are unrepresentative, so the LLM matches on CDE name alone. This produces noisy recommendations and wastes tokens.

## Decision

Filter out CDEs with more than 100 permissible values in the handler before passing them to the matching pipeline.

**Why 100?** Manual inspection of the CDE catalog shows a natural break around 100 PVs. CDEs below this threshold are categorical fields (e.g., gender, race, ethnicity) where 12 samples are representative. CDEs above are ontology-like fields where they are not. This affects roughly 8-10% of CDEs.

**Why in the handler?** The handler is the imperative shell where policy decisions belong. The DB layer (`db.py`) should return complete data, and the matcher (`matcher.py`) should match whatever it receives.

## Consequences

- Reduces noise in recommendations by excluding CDEs the LLM cannot meaningfully match via PV sampling.
- Reduces token cost (~8-10% fewer CDEs per request).
- Users will not receive recommendations for high-cardinality CDEs until a better strategy is implemented (e.g., embedding-based pre-filter, ontology lookup, or full PV indexing).
- This is a temporary measure. The filter should be removed once high-cardinality CDEs are handled properly.
