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

Requires AWS credentials and SSM parameters under `/harmonization-pipeline/{env}/`.

## API

**POST** `/{stage}/recommend`

Requires `x-api-key` header (REST API v1 usage plan).

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

Response:

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
scripts/             Operational scripts (API key management)
tests/               Unit and integration tests
adr/                 Architecture Decision Records
```
