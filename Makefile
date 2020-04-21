.PHONY: test lint

test:
	pytest

lint:
	mypy --no-incremental
	flake8 src/ tests/