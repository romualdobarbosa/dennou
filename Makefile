.PHONY: all setup lint format test demo

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

# Indexa as notas públicas de vault/examples num banco separado (chroma_demo/)
# e faz uma busca. Não toca no vault, no chroma_db/ nem no TAGS.md principais.
DEMO_ENV = DENNOU_VAULT_DIR=vault/examples DENNOU_CHROMA_DIR=chroma_demo \
	DENNOU_TAGS_FILE=chroma_demo/TAGS.md

demo:
	$(DEMO_ENV) uv run python embed.py sync
	$(DEMO_ENV) uv run python embed.py search "como criar uma branch no git"
