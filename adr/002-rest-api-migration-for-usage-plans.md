# ADR 002: Migrate HTTP APIs to REST APIs for Unified API Key Management

## Status

Accepted

## Context

Three services need gated access via a single API key (`prod_key`):

1. **Harmonization inference pipeline** (manila) — HTTP API v2 with Lambda authorizer
2. **CDE recommendation** (sarajevo) — HTTP API v2 with no auth
3. **Datastore CDE endpoints** (tokyo) — REST API v1 with usage plan

API Gateway usage plans — the native mechanism for API key throttling and quotas — only work with REST APIs (v1). HTTP APIs (v2) don't support them. The harmonization pipeline worked around this with a Lambda authorizer that checked keys against SSM parameters, but this approach doesn't integrate with usage plans and embeds plaintext keys in Terraform state.

## Decision

Convert both HTTP APIs (CDE recommendation and harmonization pipeline) to REST APIs (v1) so all three services use API Gateway's native API key + usage plan mechanism.

A centralized minting script (`scripts/associate_api_key.py`) associates any API key with all usage plans in a single operation, replacing per-service key management.

Key design choices:

- **Lambda proxy integration** — handlers already return `{"statusCode", "headers", "body"}` and read `event["body"]`, which works identically in REST API proxy mode. No handler code changes needed for CDE recommendation.
- **No api_key or usage_plan_key in Terraform** — key association is a cross-cutting concern managed by the minting script, not individual workspaces.
- **Binary media types for harmonization** — `binary_media_types = ["*/*"]` preserves gzip/base64 body handling.

## Alternatives Considered

**Lambda authorizer with SSM-backed key list**: Already in use for harmonization. Doesn't integrate with usage plans (no throttling/quotas), requires maintaining authorizer Lambda code, and stores plaintext keys in Terraform state.

**CloudFront + API key validation**: Adds a CDN layer that's unnecessary for API-to-API traffic. Increases latency and operational complexity without meaningful benefit.

**Keep HTTP APIs and build custom throttling**: Would require implementing rate limiting in application code or a separate service, duplicating what API Gateway provides natively.

## Consequences

- **Breaking URL change**: REST API invoke URLs include the stage name segment (`/<stage>/recommend` instead of `/recommend`). Clients must update URLs. Coordinate infrastructure and client deploys to minimize downtime.
- **Lambda authorizer eliminated**: Removes the `auth_http` Lambda, its IAM role, and SSM key lookups from the harmonization pipeline. Simpler architecture.
- **Plaintext key removed from Terraform state**: Keys are associated via API calls, not declared as Terraform resources.
- **In-flight job principal mismatch (harmonization)**: Existing DynamoDB jobs have `owner="api-key"` from the old authorizer. After migration, `extract_principal` returns the `apiKeyId` string. Deploy during a drain window with no in-flight jobs.
- **Unified key management**: Adding or rotating keys is a single script invocation instead of updating multiple Terraform workspaces.
