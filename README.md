```
    ██████╗ ███████╗███╗   ██╗███╗   ██╗ ██████╗ ██╗   ██╗
    ██╔══██╗██╔════╝████╗  ██║████╗  ██║██╔═══██╗██║   ██║
    ██║  ██║█████╗  ██╔██╗ ██║██╔██╗ ██║██║   ██║██║   ██║
    ██║  ██║██╔══╝  ██║╚██╗██║██║╚██╗██║██║   ██║██║   ██║
    ██████╔╝███████╗██║ ╚████║██║ ╚████║╚██████╔╝╚██████╔╝
    ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝
      電脳 · cérebro eletrônico · RAG sobre Zettelkasten


Personal knowledge base with semantic search. Notes are stored as Markdown in an Obsidian vault and indexed in a local vector database for RAG-powered retrieval.

## Stack

- **Obsidian** — note editor and graph view
- **ChromaDB** — local vector database
- **Sentence Transformers** (`paraphrase-multilingual-MiniLM-L12-v2`) — local embeddings, multilingual, no API required
- **Claude Code** — agent that creates notes and queries the vault before answering

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
make setup   # uv sync (creates .venv, Python 3.12) + generates TAGS.md
make demo    # indexes the example notes in vault/examples and runs a search
```

> The deps (`torch` via `sentence-transformers`) lack wheels for very new Python
> releases, so the project pins 3.12. Run the scripts with `.venv/bin/python3`.

`vault/examples/` has a few public sample notes. `make demo` indexes them into a
separate store (`chroma_demo/`), so it never mixes with your own notes in `vault/`.
Paths and model can be overridden with `DENNOU_VAULT_DIR`, `DENNOU_CHROMA_DIR`,
`DENNOU_TAGS_FILE` and `DENNOU_MODEL`.

Dev: `make lint`, `make format`, `make test`, `make eval-quick`. CI
(`.github/workflows/ci.yml`) runs lint, tests and the `eval-quick` retrieval
gate on every push to `main` and on pull requests. It installs the CPU build of
torch, so it never downloads the CUDA libraries the lockfile pulls on Linux.

Open `vault/` as an Obsidian vault.

## Usage

Talk to the agent naturally. It searches the vault before answering and cites relevant notes when found.

To save a note, ask explicitly:

> "salva isso" / "cria uma nota" / "anota aí"

The agent picks the right note type, fills the frontmatter, and indexes it automatically.

### CLI

```bash
# index a specific note
.venv/bin/python3 embed.py add vault/20260528210249-left-join-sql.md

# semantic search (top 5 notes, optional filters)
.venv/bin/python3 embed.py search "window functions"
.venv/bin/python3 embed.py search "undo a commit" --type command --tag git -k 3

# rebuild the whole index from scratch
.venv/bin/python3 embed.py sync
```

### How search works

Each note is split into chunks of up to 128 tokens (the model's limit), grouping
whole paragraphs and putting the title in front of every chunk. A note's score
is the score of its best chunk, each note shows up once in the results, and the
excerpt is the chunk that matched. Before this, long notes were cut at 128
tokens and everything after that was invisible to search. I picked this setup
with the retrieval eval in `eval/` (see `eval/results/summary.md`).

Search always prints the top 5 and flags the ones under the relevance cut,
0.55 by default (`DENNOU_SCORE_THRESHOLD`). The agent ignores those. The cut
also came from the eval, and it only makes sense for this model and chunking.

`sync` builds a new index and swaps it in at the end, so notes deleted from the
vault drop out of it. If your `chroma_db/` was built before chunking (one vector
per note), `search` and `add` warn about it, and one `embed.py sync` migrates it.

Every CLI search appends a JSON line to `logs/search.jsonl` with the query, the
note ids and scores, how many passed the cut, latency and model. `logs/` is
gitignored since those are personal queries. Set `DENNOU_LOG_FILE` to another
path, or to `off` to disable it.

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
- **Session memory** — the bot keeps the conversation going between messages
  (it stores the session id in `.bot_session` and resumes it), so follow-ups
  like "salva isso" see the previous answer. Send `/novo` (or `/reset`) to start
  a fresh conversation.

### Create your own bot (step by step)

The bot is single-tenant: each person runs **their own copy** (see *Cost & security*
below). To set up yours:

1. **Create the bot on Telegram.** Open the app, search for **@BotFather** (the
   verified one), and send `/newbot`. Pick a display name (e.g. `dennou`) and a
   username that must end in `bot` (e.g. `dennou_notes_bot`). BotFather replies
   with a **token** like `123456789:AA...` — this is the bot's password, keep it
   secret.
2. **Configure the project.**
   ```bash
   cp .env.example .env
   ```
   Paste the token into `TELEGRAM_BOT_TOKEN`. Leave `TELEGRAM_OWNER_ID` empty
   for now. (`DENNOU_BOT_MODEL` is optional — defaults to `sonnet`.)
3. **Discover your `TELEGRAM_OWNER_ID`.** Send any message (e.g. `oi`) to your
   new bot in Telegram, then ask the Telegram API for your chat id:
   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][-1]['message']['chat']['id'])"
   ```
   Put that number in `TELEGRAM_OWNER_ID` in `.env`.
4. **Run and test.**
   ```bash
   python3 bot.py
   ```
   Message the bot: ask a question, then say "salva isso" to create a note.

> The bot only replies *after* you message it first — Telegram doesn't let bots
> start a conversation. Any message from a `chat_id` other than the owner's is
> rejected and logged as `[lock] chat_id não autorizado: <id>`.

### Cost & security — who pays, who can use it

The bot runs `claude -p` **on the host machine using the owner's Claude
authentication** (the Claude Code login / API key on that machine). The Telegram
user does **not** attach their own Claude account — the API has no idea who is on
the other end of the chat.

That means **whoever talks to the bot spends the owner's Claude plan and writes to
the owner's vault**, running on the owner's machine. This is exactly why the
`TELEGRAM_OWNER_ID` lock exists: without it, anyone who found the bot's @username
could burn your credits and touch your files (even with `ALLOWED_TOOLS` restricted,
they could still read/write the vault).

So there is no "shared" dennou bot — if someone else wants one, they run their own
instance on their own machine, with their own Telegram bot token, their own
`TELEGRAM_OWNER_ID`, and their own Claude authentication. One instance per
person/machine.

### Run as a service (systemd, user)

The unit assumes the repo at `~/dennou` (edit the `%h/dennou` paths otherwise).

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
│   └── examples/   # public sample notes (used by make demo)
├── chroma_db/      # Vector database (gitignored)
├── embed.py        # Embedding and search pipeline
├── bot.py          # Telegram bot (headless agent bridge)
├── CLAUDE.md       # Agent instructions
└── SCHEMA.md       # Note schema and templates
```
