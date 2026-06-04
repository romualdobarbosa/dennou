# Dennou 電脳

Personal knowledge base with semantic search. Notes are stored as Markdown in an Obsidian vault and indexed in a local vector database for RAG-powered retrieval.

## Stack

- **Obsidian** — note editor and graph view
- **ChromaDB** — local vector database
- **Sentence Transformers** (`paraphrase-multilingual-MiniLM-L12-v2`) — local embeddings, multilingual, no API required
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

## Telegram bot

Talk to dennou from Telegram. The bot forwards your message to the Claude Code
agent in headless mode (`claude -p`), which follows the same `CLAUDE.md` rules
(searches the vault, answers, saves a note when asked) and replies back.

- **Long polling** via stdlib — no public URL/webhook, works behind a home router.
- **Runs on the PC** so notes are saved locally. Use the systemd service to keep
  it alive without a terminal open.
- **Locked to your `chat_id`** — only the owner can drive it, since it writes
  files and runs `embed.py` on the machine.
- **Restricted tools** — the headless agent may only run `embed.py` and read/write
  vault files (`ALLOWED_TOOLS` in `bot.py`).

### Setup

```bash
cp .env.example .env      # fill TELEGRAM_BOT_TOKEN (from @BotFather) and TELEGRAM_OWNER_ID
python3 bot.py            # run in the foreground to test
```

To discover your `TELEGRAM_OWNER_ID`: run the bot with the token set, message it,
and read the `[lock] chat_id não autorizado: <id>` line in the log.

### Run as a service (systemd, user)

```bash
mkdir -p ~/.config/systemd/user
cp dennou-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dennou-bot
journalctl --user -u dennou-bot -f      # logs
```

> **RAG caveat:** notes created/edited from the phone (Obsidian) are only indexed
> when `embed.py add` runs on the PC. Re-embed new notes periodically.

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
├── bot.py          # Telegram bot (headless agent bridge)
├── CLAUDE.md       # Agent instructions
└── SCHEMA.md       # Note schema and templates
```
