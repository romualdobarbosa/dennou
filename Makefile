.PHONY: all setup lint format test demo eval eval-quick

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

# Eval de retrieval no vault sintético de eval/vault (não toca no vault real).
# eval: as 12 configs (3 modelos x nota inteira/chunks x com/sem título) e o
# experimento do related; grava eval/results/. Baixa e5-small e bge-m3 (~2.5 GB).
eval:
	uv run python -m eval.run_eval

# Gate do CI: 10 perguntas fixas com a config de produção. Hoje dá Recall@5 = 1.0;
# o mínimo de 0.8 tolera até 2 erros antes de falhar.
EVAL_QUICK_MIN_RECALL ?= 0.8

eval-quick:
	uv run python -m eval.run_eval --quick --min-recall5 $(EVAL_QUICK_MIN_RECALL)
