.PHONY: lint typecheck test all

lint:
	uv run ruff check src tests

typecheck:
	uv run basedpyright src tests

test:
	uv run pytest tests -v

all: lint typecheck test
