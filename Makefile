.PHONY: dev test lint format build clean

dev:
	pip install -e ".[dev]"

test:
	pytest -v --cov=vn_corporate_actions --cov-report=term-missing

lint:
	ruff check src tests
	mypy src

format:
	black src tests
	ruff check --fix src tests

build:
	python -m build

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
