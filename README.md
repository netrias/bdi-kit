# cde-recommend

AWS Lambda service that matches source dataset columns to Common Data Elements (CDEs) using OpenAI structured output.

## Quick start

```bash
uv sync --all-extras          # install deps (runtime + dev)
make all                      # lint + typecheck + test
```

## Deploy

```bash
make deploy-staging           # build + terraform apply to staging
make deploy-plan              # terraform plan only (no apply)

# Production
PYTHONPATH=. uv run python -m deploy.deploy --env prod
```

Requires AWS credentials with access to:

- **SSM Parameter Store** (read) — secrets loaded automatically during deploy:
  - `/harmonization-pipeline/{env}/openai-api-key` → `TF_VAR_openai_api_key`
  - `/harmonization-pipeline/{env}/zero-shot-db-user` → `TF_VAR_db_user`
  - `/harmonization-pipeline/{env}/zero-shot-db-password` → `TF_VAR_db_password`
- **S3** — Terraform state backend (auto-bootstrapped)
- **API Gateway, Lambda, DynamoDB** — infrastructure managed by Terraform

## API

**POST** `/{stage}/recommend`

Requires `x-api-key` header (REST API v1 usage plan).

### Request

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_schema` | string | yes | Data model key (e.g. `"ccdi"`) |
| `target_version` | int, string, or `"latest"` | no | Version number, label, or `"latest"` (default) |
| `data` | object | yes | Map of column names to sample value arrays |
| `top_k` | int | no | Max matches per column (default: 5) |

```json
{
  "target_schema": "ccdi",
  "target_version": 1,
  "data": {
    "sex": ["Male", "Female", "Unknown"],
    "diagnosis": ["Acute Lymphoblastic Leukemia", "Neuroblastoma"]
  }
}
```

### Response

Each column returns up to `top_k` matches ranked by confidence. Columns that are numeric or id-like return a single `No_Matches_Found` entry.

```json
{
  "results": {
    "sex": [
      { "target": "gender", "similarity": 0.95, "target_cde_id": 1 }
    ],
    "diagnosis": [
      { "target": "diagnosis", "similarity": 0.88, "target_cde_id": 42 }
    ]
  }
}
```

| Field | Description |
|-------|-------------|
| `target` | Matched CDE key name |
| `similarity` | Confidence score (0.0–1.0) |
| `target_cde_id` | CDE database ID |

## Matching strategy

Each source column goes through profiling and filtering before reaching the LLM:

1. **Profile** — classify column dtype as `numeric`, `id_like`, `categorical`, `free_text`, or `mixed`
2. **Filter** — `numeric` and `id_like` columns return `No_Matches_Found` immediately (no LLM call). CDEs with >100 permissible values are excluded from matching candidates.
3. **Match** — route by CDE count:
   - **Single-call** (<=500 CDEs): one OpenAI call per column with all CDEs in the developer message
   - **Chunked** (>500 CDEs): split CDEs into 50-CDE chunks, shortlist top-3 per chunk, then final ranking over the aggregated shortlist
4. **Cache** — results are cached in DynamoDB (30-day TTL) keyed by data model + version + column name + sorted values. Cache hits skip profiling and LLM calls entirely.

The developer message (CDE catalog) is built once per batch and reused across all columns for OpenAI prompt caching.

## Development

| Command            | Description                     |
|--------------------|---------------------------------|
| `make lint`        | Ruff linter                     |
| `make typecheck`   | basedpyright (standard mode)    |
| `make test`        | pytest                          |
| `make all`         | All three                       |
| `make clean`       | Remove build artifacts          |

## Project layout

```
src/cde_recommend/   Lambda source (handler, matching, profiling, caching)
deploy/              Deploy orchestrator (packaging, secrets, terraform)
infra/               Terraform/OpenTofu configuration
tests/               Unit and integration tests
adr/                 Architecture Decision Records
```
