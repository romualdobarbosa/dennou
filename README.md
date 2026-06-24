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
