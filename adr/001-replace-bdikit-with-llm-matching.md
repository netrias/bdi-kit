# ADR 001: Replace bdi-kit with LLM-based CDE Matching

## Status

Accepted

## Context

bdi-kit used embedding-based schema matching (Magneto, Valentine, contrastive learning) to match source columns to CDEs. These approaches required ML model downloads (~2GB+), GPU inference for acceptable latency, and complex dependency chains (torch, transformers, flair, magneto-python, polyfuzz). Deployment to Lambda was impractical due to package size limits and cold-start times.

The matching quality from embedding-based approaches was adequate but not significantly better than what modern LLMs achieve in a single structured-output call, especially when CDE permissible values are included as context.

## Decision

Replace the entire bdi-kit library with a single Lambda service that uses OpenAI's structured output API to match columns to CDEs:

- **Single Lambda** with asyncio parallelism (not Step Functions fan-out)
- **Pre-parsed column input** — caller sends column names + values
- **Index-based output** — LLM returns candidate indices, not strings, preventing hallucinated CDE keys
- **Three-layer caching** — RDS CDE cache (warm start), DynamoDB result cache (repeated datasets), OpenAI prompt caching (developer role prefix)
- **Single-call default** for ≤500 CDEs; chunked shortlisting fallback for >500

## Consequences

- **Simpler deployment**: No ML models, no GPU. Lambda cold start is fast.
- **External dependency on OpenAI**: Matching quality and latency depend on OpenAI API availability and model performance.
- **Cost per call**: Each column match costs ~$0.003 (gpt-5-mini). Prompt caching reduces this for batch operations.
- **No offline capability**: Requires network access to both RDS and OpenAI.
