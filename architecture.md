# Architecture

## Overview

A single AWS Lambda behind REST API Gateway. Takes a dataset (column names + sample values) and a target data model, returns ranked CDE matches per column. Uses OpenAI structured output for matching, PostgreSQL (RDS) for CDE catalog storage, and DynamoDB for result caching.

## Request flow

```
Client
  -> API Gateway (REST v1, x-api-key auth)
    -> Lambda handler (handler.py)
      1. Parse request, validate inputs
      2. Load CDEs from RDS (db.py, warm-start cache)
      3. Filter high-cardinality CDEs (>100 PVs)
      4. Fan out column matching (batch.py)
         a. Check DynamoDB cache
         b. Profile each column (profiler.py)
         c. Skip numeric/id-like columns
         d. Call OpenAI per uncached column (matcher.py -> openai_client.py)
         e. Store new results in DynamoDB cache
      5. Format response (netrias_client contract)
```

## Module responsibilities

| Module | Responsibility | Changes when... |
|--------|---------------|-----------------|
| `handler.py` | Lambda entry point, request parsing, response formatting | API contract or validation rules change |
| `batch.py` | Multi-column orchestration, cache coordination | Caching strategy or column filtering logic changes |
| `matcher.py` | Single-column matching (single-call or chunked) | Matching algorithm or chunking strategy changes |
| `profiler.py` | Column type inference and value sampling | Profiling heuristics change |
| `serialization.py` | CDE/column prompt construction | Prompt format changes |
| `schema.py` | OpenAI structured output JSON schema | Output format changes |
| `openai_client.py` | AsyncOpenAI wrapper | OpenAI API evolves |
| `cache.py` | DynamoDB result caching | Cache strategy changes |
| `db.py` | RDS connection and CDE loading | DB schema changes |
| `types.py` | Domain types (dataclasses + Pydantic models) | Data model or API contract changes |

## Key design decisions

Recorded in `adr/`:

1. **LLM over embeddings** (ADR 001) — Replaced bdi-kit's ML-based matching with OpenAI structured output. Simpler deployment, no GPU, competitive quality.
2. **REST API v1** (ADR 002) — All services use API Gateway usage plans for unified key management. Replaced HTTP API v2 + Lambda authorizer.
3. **High-cardinality CDE filter** (ADR 003) — Temporary exclusion of CDEs with >100 permissible values. LLM can't meaningfully match from 12 samples when the full set is thousands.

## Three-layer caching

1. **RDS warm-start cache** — `db.py` caches CDE lists in-process (`_cde_cache`). Avoids DB round-trip on warm Lambda invocations.
2. **DynamoDB result cache** — `cache.py` stores column match results keyed by SHA-256 of (dm_key, version, column_name, values). 30-day TTL.
3. **OpenAI prompt caching** — The developer message (CDE list) is identical across all columns in a batch. OpenAI caches this prefix, reducing per-column token cost.

## Matching strategy

For **<=500 CDEs** (default): single OpenAI call per column with all CDEs in the developer message.

For **>500 CDEs**: chunked shortlisting — split CDEs into chunks of 50, get top-3 per chunk, aggregate, then do a final ranking call over the shortlist.

The LLM returns candidate **indices** (not strings) into the CDE list, preventing hallucinated CDE keys.

## Infrastructure

Managed by OpenTofu in `infra/`. Deploy via `deploy/`:

- Lambda (Python 3.12, x86_64)
- REST API Gateway with usage plan + API key
- DynamoDB cache table (on-demand billing, 30-day TTL)
- IAM role with DynamoDB + VPC access
- S3/DynamoDB terraform state backend (bootstrapped by deploy script)

## Deploy system

`deploy/` is a Python package invoked as `uv run python -m deploy.deploy`:

1. Load secrets from SSM -> `TF_VAR_*` env vars
2. Build Lambda ZIP (cross-compiled for Linux x86_64)
3. Bootstrap terraform backend (S3 + DynamoDB)
4. `tofu init` + `tofu apply`
