.PHONY: lint typecheck test all deploy-plan deploy-staging clean

lint:
	uv run ruff check src tests deploy

typecheck:
	uv run basedpyright src tests deploy

test:
	uv run pytest tests -v

all: lint typecheck test

deploy-plan:
	uv run python -m deploy.deploy --env staging --plan

deploy-staging:
	uv run python -m deploy.deploy --env staging

clean:
	rm -rf build/ .pytest_cache/ .ruff_cache/
