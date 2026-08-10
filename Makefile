.PHONY: install train test lint eda

install:  ## Create the environment from the lock file
	uv sync

train:  ## Reproduce every number quoted in README.md and INSIGHTS.md
	uv run python -m term_deposit.cli

test:
	uv run pytest -q

lint:
	uv run ruff check src tests

eda:  ## Re-execute the exploratory notebook in place
	uv run jupyter execute notebooks/01_eda.ipynb --inplace
