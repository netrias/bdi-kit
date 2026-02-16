.PHONY: lint typecheck test all plan-staging plan-prod deploy-staging deploy-prod clean

lint:
	uv run ruff check src tests deploy scripts

typecheck:
	uv run basedpyright src tests deploy scripts

test:
	uv run pytest tests -v

all: lint typecheck test

plan-staging:
	uv run python -m deploy.deploy --env staging --plan

plan-prod:
	uv run python -m deploy.deploy --env prod --plan

deploy-staging:
	uv run python -m deploy.deploy --env staging

deploy-prod:
	uv run python -m deploy.deploy --env prod

clean:
	rm -rf build/ .pytest_cache/ .ruff_cache/
