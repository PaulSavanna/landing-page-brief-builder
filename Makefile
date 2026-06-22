.PHONY: install run test lint docker-build

install:
	python -m pip install -e ".[dev]"

run:
	uvicorn app:app --reload --port 8000

test:
	pytest

lint:
	ruff check .

docker-build:
	docker build -t landing-brief-builder .
