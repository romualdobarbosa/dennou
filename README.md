# Dennou 電脳

Personal knowledge base with semantic search. Notes are stored as Markdown in an Obsidian vault and indexed in a local vector database for RAG-powered retrieval.

## Stack

- **Obsidian** — note editor and graph view
- **ChromaDB** — local vector database
- **Sentence Transformers** (`all-MiniLM-L6-v2`) — local embeddings, no API required
- **Claude Code** — agent that creates notes and queries the vault before answering

## Setup

```bash
pip install -r requirements.txt
```

Open `vault/` as an Obsidian vault.

## Usage

Talk to the agent naturally. It searches the vault before answering and cites relevant notes when found.

To save a note, ask explicitly:

> "salva isso" / "cria uma nota" / "anota aí"

The agent picks the right note type, fills the frontmatter, and indexes it automatically.

### CLI

```bash
# index a specific note
python3 embed.py add vault/20260528210249-left-join-sql.md

# semantic search
python3 embed.py search "window functions"

# reindex entire vault
python3 embed.py sync
```

## Note types

| Type | Use |
|------|-----|
| `syntax` | Language syntax — Python, SQL, regex |
| `concept` | Theory, concept explanation |
| `command` | Terminal commands, CLI tools |
| `error` | Bugs, debug, solutions |
| `fact` | Facts, curiosities |
| `note` | Free-form notes |

## Structure

```
dennou/
├── vault/          # Markdown notes (Obsidian vault)
├── chroma_db/      # Vector database (gitignored)
├── embed.py        # Embedding and search pipeline
├── CLAUDE.md       # Agent instructions
└── SCHEMA.md       # Note schema and templates
```
