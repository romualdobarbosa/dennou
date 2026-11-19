.PHONY: all setup lint format test

all: lint test

# Cria a .venv (uv sync) e gera o TAGS.md, que o agente lê ao criar notas.
setup:
	uv sync
	uv run python embed.py tags

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest
