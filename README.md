# dennou (電脳)

I keep what I learn as small Markdown notes, and I wanted to ask a question and get the answer from them, in the terminal or on my phone, knowing how often the search actually finds the right note.

[![CI](https://github.com/romualdobarbosa/dennou/actions/workflows/ci.yml/badge.svg)](https://github.com/romualdobarbosa/dennou/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](.python-version)

> **TL;DR (pt-BR).** Base de conhecimento pessoal com RAG local. As notas ficam num vault do Obsidian, o `embed.py` indexa em chunks no ChromaDB com um modelo multilíngue do Sentence Transformers, e um agente Claude Code consulta o índice antes de responder, no terminal ou por um bot do Telegram. Um eval de retrieval com 80 notas sintéticas e 60 perguntas rotuladas escolheu o modelo, o chunking e o corte de relevância, e um subconjunto de 10 perguntas roda como gate no CI.

**TL;DR.** A local RAG setup over an Obsidian vault of Markdown notes. `embed.py` splits each note into title-prefixed chunks, embeds them with a multilingual Sentence Transformers model and stores them in ChromaDB. A Claude Code agent searches that index before it answers, either in the terminal or headless (`claude -p`) behind a Telegram bot locked to one chat. A retrieval evaluation harness (80 synthetic notes, 60 graded queries, 12 configs) picked the model, the chunking and the 0.55 relevance cut, and a 10-query subset runs as a regression gate in CI.

## Evaluation

My real vault is private, so I built a public one for the eval. It has 80 notes in Portuguese about Python, SQL, Git and Linux, written in the same format as the real notes ([`eval/vault/`](eval/vault/)), and 60 queries with graded relevance labels ([`eval/queries.jsonl`](eval/queries.jsonl)). 25 queries use the note's own words, 15 are beginner paraphrases that avoid them, 10 are in English against Portuguese notes, and 10 have no answer in the vault. Twelve of the answerable queries only have their answer after roughly 400 words of a long note. The dataset is described in [`eval/README.md`](eval/README.md).

The harness ([`eval/run_eval.py`](eval/run_eval.py)) has no copy of the production logic. It calls the same `embed.py` functions to parse notes, chunk them, write them to Chroma and merge chunks back into one score per note, and it reads the cut from the same constant. Every config indexes `eval/vault` into a temporary Chroma collection, so the eval never touches the real vault.

### Results

From [`eval/results/summary.md`](eval/results/summary.md) (50 answerable queries, CPU). Production is the bold row.

| config | Recall@1 | Recall@5 | MRR | nDCG@5 | FP@0.55 | Recall@5 tail | p50 ms |
|---|---|---|---|---|---|---|---|
| minilm-whole-title (before) | 0.700 | 0.880 | 0.779 | 0.775 | 0% | 0.750 | 14.1 |
| minilm-whole-notitle | 0.660 | 0.920 | 0.766 | 0.793 | 0% | 0.833 | 13.8 |
| **minilm-chunk-title (production)** | 0.720 | 0.960 | 0.802 | 0.832 | 10% | 1.000 | 10.6 |
| minilm-chunk-notitle | 0.700 | 0.960 | 0.799 | 0.813 | 20% | 1.000 | 11.3 |
| e5-small-whole-title | 0.720 | 0.860 | 0.780 | 0.769 | 100% | 0.833 | 14.5 |
| e5-small-whole-notitle | 0.700 | 0.880 | 0.777 | 0.765 | 100% | 0.833 | 14.8 |
| e5-small-chunk-title | 0.740 | 0.900 | 0.821 | 0.808 | 100% | 0.917 | 14.5 |
| e5-small-chunk-notitle | 0.800 | 0.900 | 0.843 | 0.831 | 100% | 0.917 | 13.1 |
| bge-m3-whole-title | 0.820 | 0.900 | 0.859 | 0.839 | 0% | 0.917 | 80.8 |
| bge-m3-whole-notitle | 0.820 | 0.900 | 0.859 | 0.825 | 0% | 0.917 | 84.8 |
| bge-m3-chunk-title | 0.820 | 0.900 | 0.862 | 0.849 | 20% | 0.917 | 79.9 |
| bge-m3-chunk-notitle | 0.840 | 0.920 | 0.873 | 0.850 | 10% | 0.917 | 79.6 |

The three models are `paraphrase-multilingual-MiniLM-L12-v2` (production), `intfloat/multilingual-e5-small` (with the `query: ` and `passage: ` prefixes it was trained with) and `BAAI/bge-m3`. "whole" puts title and body in one vector, "chunk" splits the note, "title/notitle" says whether the title goes into the embedded text.

### Metrics

- Recall@k is 1 when at least one note graded 2 ("answers the question") shows up in the top k.
- MRR is the mean of 1/rank of the first grade-2 note, looking at the top 10.
- nDCG@5 uses the grade (2 or 1) as gain, with log2 discount, normalized by the ideal ranking of the labeled notes.
- FP@0.55 is the share of the 10 no-answer queries whose top result scores 0.55 or more, which means the agent would use a note that answers nothing.
- Recall@5 tail is Recall@5 on the 12 queries whose answer sits at the end of a long note.
- Latency is query encoding plus the Chroma query, after a warm-up call.

### Whole notes against chunks

The old pipeline embedded title and body as one vector. `paraphrase-multilingual-MiniLM-L12-v2` has `max_seq_length = 128`, and the tokenizer cuts anything past that without a warning. All 80 eval notes go over 128 tokens, so the end of every note was invisible to search. On the tail queries, the whole-note config got Recall@5 0.750. Splitting notes into chunks of up to 128 tokens (title in front of each, counted in the limit, so no chunk gets cut) took that to 1.000. Overall Recall@5 went from 0.880 to 0.940 with chunks alone, and to 0.960 after I also dropped the `## Links` section (below).

### How the 0.55 cut was picked

`embed.py search` always prints the top 5 and flags the ones below the cut. Until November 2026 the agent ignored those (now the score is only a hint, see [Answer evaluation](#answer-evaluation)). For each config the harness sweeps the cut from 0.0 to 1.0 in steps of 0.05 and computes two things, the false positive rate on the 10 no-answer queries and Recall@5 counting only notes above the cut. The suggested cut is the one with the highest recall at no more than 10% false positives. For production that is 0.55 (Recall@5 0.740 above the cut, 10% FP). The old cut was 0.4, and it had never been measured. Scores are not comparable across models (with e5 almost everything scores above 0.7, so FP@0.55 is 100%), so the cut only holds for this model and chunking.

### Three more experiments

#### Expanding results with the `related` field (not adopted)

Every note lists related note ids in its frontmatter. I tried giving the notes related to the top 3 a score of max(own score, λ × parent score), with λ = 0.8, 0.9 and 1.0, on the best config by nDCG@5 (not production). In an earlier run, on bge-m3-chunk-title with the Links section still embedded, λ = 1.0 took Recall@5 from 0.900 to 0.940, but λ was picked on the same 50 queries it was measured on (results committed in [`65c09c2`](https://github.com/romualdobarbosa/dennou/commit/65c09c2)). In the current run the best config is bge-m3-chunk-notitle and no λ improves Recall@5 (λ = 1.0 drops it from 0.920 to 0.900, see [`related_expansion.json`](eval/results/related_expansion.json)). Search does not use `related`.

#### Leaving the `## Links` section out of the embedded text (adopted)

Notes end with Obsidian wiki-links to other notes. Embedded, they are text made of other notes' file names. Same production config, with and without the section ([`links_section.json`](eval/results/links_section.json)):

| variant | Recall@5 | nDCG@5 | MRR | FP@0.55 | Recall@5 above 0.55 | chunks |
|---|---|---|---|---|---|---|
| with `## Links` | 0.940 | 0.819 | 0.799 | 10% | 0.740 | 516 |
| **without `## Links` (production)** | 0.960 | 0.832 | 0.802 | 10% | 0.740 | 475 |

One more English query lands in the top 5 and the false positive rate stays the same, so production now strips the section before chunking. I started this because `make demo` ranks `git commit` above `git branch` for "como criar uma branch no git", and it still does without the Links section. On those five short notes the links were never a chunk of their own, and the `git commit` example chunk mentions a feature branch.

#### Hybrid search and reranking (not adopted)

On top of the production ranking I tried BM25 alone, two fusions with the vector score (RRF with k = 60, and a × cosine + (1 − a) × normalized BM25 with a = 0.5, 0.7 and 0.9), and reranking the top 20 with two multilingual cross-encoders ([`hybrid_rerank.json`](eval/results/hybrid_rerank.json)). The cut stays on the cosine score, so FP@0.55 is 10% for every variant.

| variant | Recall@1 | Recall@5 | MRR | Recall@5 above 0.55 | extra latency (p50) |
|---|---|---|---|---|---|
| **vector (production)** | 0.720 | 0.960 | 0.802 | 0.740 | 0 |
| BM25 only | 0.820 | 0.860 | 0.842 | 0.740 | 0.1 ms |
| RRF | 0.820 | 0.920 | 0.856 | 0.740 | 0.1 ms |
| 0.7 × cosine + 0.3 × BM25 | 0.860 | 0.940 | 0.896 | 0.740 | 0.1 ms |
| rerank, mmarco-mMiniLMv2-L12 | 0.880 | 0.940 | 0.907 | 0.740 | 4.5 s |
| rerank, bge-reranker-v2-m3 | 0.880 | 0.980 | 0.918 | 0.740 | 58 s |

Weighted fusion puts the right note first much more often for almost no cost, but loses an English query from the top 5, since BM25 can't match English words against Portuguese notes. bge-reranker-v2-m3 wins on every metric and takes about a minute per search on CPU. None of them changes Recall@5 above the cut, because reordering doesn't change which notes pass 0.55, and the agent reads every note that passes. The right note is in the top 5 for 96% of the queries but scores above 0.55 for 74%, so the cut is the next thing to work on, not the order.

### Answer evaluation

Retrieval stops at the top 5. The right note was there for 96% of the queries but scored above 0.55 for 74%, and the agent skipped everything below the cut. So I measured the other end, whether the agent uses the right note and whether the answer is faithful to it. Two scripts call `claude -p`. Sonnet answers, and Opus judges whether the answer is correct and whether what it credits to a note is actually in that note.

The controlled run ([`run_generation_eval.py`](eval/run_generation_eval.py), [results](eval/results/generation/summary.md)) does the search itself, puts the notes each rule lets through into the prompt in full, and the model answers with no tools, returning the ids of the notes it used. All 60 queries:

| rule | right note in the prompt | cited the right note | faithful | false positives | mean prompt |
|---|---|---|---|---|---|
| A: only notes ≥ 0.55 (the old rule) | 74% | 74% | 98% | 0 of 10 | 3,706 chars |
| B: ≥ 0.55 plus a "maybe" band from 0.45 to 0.55 | 84% | 84% | 100% | 0 of 10 | 6,130 chars |
| C: the whole top 5 with scores, the model decides | 96% | 96% | 98% | 0 of 10 | 11,686 chars |

When the right note reaches the model, the model uses it. On paraphrases, citing the right note went from 27% (A) to 87% (C). Even with the whole top 5 in front of it, it cited nothing on the 10 no-answer queries, including the one whose top result scores above 0.55. The judge's "correct" was 100% everywhere and tells the rules apart in nothing, since Sonnet knows Git and SQL without the vault.

In real use the model doesn't get whole notes. `search` prints a 200-character excerpt and the agent decides whether to open the file. The agent run ([`run_agent_eval.py`](eval/run_agent_eval.py), [results](eval/results/agent/summary.md)) runs dennou itself. Each query is a `claude -p` with the same tools and permissions as `bot.py`, in a copy of the project with the eval vault. Both rules use the same `CLAUDE.md` except for the paragraph about the cut. The 35 queries where the cut matters (paraphrase, English, no-answer):

| rule | searched the vault | cited the right note | right note only below 0.55: cited | false positives | faithful | notes opened per query | mean time |
|---|---|---|---|---|---|---|---|
| cut: skip notes below 0.55 | 97% | 76% | 0 of 4 | 0 of 10 | 94% | 0.1 | 14 s |
| **hint: the score is a hint, open the note before using it (production)** | 100% | 96% | 5 of 5 | 0 of 10 | 94% | 0.8 | 14 s |

The agent rewrites the query before searching (sometimes adding English terms), which moves the scores, so the number of queries with the right note only below the cut differs between rules (4 and 5). With the new rule it recovered all of them, cited nothing on no-answer queries, and took no extra time. Each rule had two unfaithful answers. Under "hint" it opened the note and still credited it with things from its own knowledge. Under "cut" it cited a note from the excerpt alone and got wrong what the note says. `CLAUDE.md` now uses the hint rule. In an earlier run with the old `CLAUDE.md`, the agent skipped the search on three paraphrases (it read "I reverted the project to an old version" as a question about the directory it runs in), so `CLAUDE.md` now tells it to always search, and the numbers above include that.

One run per query, the cut column rests on 4 or 5 cases, and the judge is the same model family as the answerer. The agent run cost about US$4.70 at list price and the controlled one about US$8.50, both through a Claude subscription. If you reproduce it, Claude Code doesn't load a `CLAUDE.md` from a directory under `/tmp`, so the project copy lives in `~/.cache/dennou-agent-eval`.

### Caveats

- 50 answerable and 10 no-answer queries is a small set. Each no-answer query is worth 10 points of false positive rate, so 10% means one query.
- I wrote the notes and the queries (with an agent's help), so the queries lean toward the notes' vocabulary. Paraphrase and cross-lingual queries are there to soften that, not to remove it. The numbers are good for comparing retrieval versions against each other, not as an absolute measure.
- There is no held-out query set. Every choice here (model, chunking, cut, the λ values of the related experiment) was made on the same 60 queries it is reported on.
- Answer quality is measured on 60 (controlled) and 35 (agent) queries with one run each, judged by a model from the same family. See [Answer evaluation](#answer-evaluation).

### Reproduce

```bash
make eval         # 12 configs + related, Links and hybrid search experiments, writes eval/results/
make eval-quick   # CI gate: production config, 10 fixed queries, fails below Recall@5 0.8
uv run python -m eval.run_generation_eval   # answer eval, controlled (needs the claude CLI)
uv run python -m eval.run_agent_eval        # answer eval, real agent (needs the claude CLI)
```

`make eval` runs on CPU and downloads e5-small, bge-m3 and the two rerankers the first time (about 5 GB in the Hugging Face cache). The bge-reranker-v2-m3 part alone takes about 2 hours on CPU; `uv run python -m eval.run_eval --rerankers mminilm` skips it. `make eval-quick` runs on every push and pull request in [CI](.github/workflows/ci.yml) and currently gives Recall@5 0.9 (q026, a paraphrase about `git revert`, misses in the full eval too).

## By the numbers

| Metric | Value | Source |
|---|---|---|
| Recall@5, production config | 0.960 | [`eval/results/summary.md`](eval/results/summary.md) |
| nDCG@5, production config | 0.832 | [`eval/results/summary.md`](eval/results/summary.md) |
| MRR, production config | 0.802 | [`eval/results/summary.md`](eval/results/summary.md) |
| Recall@5 before chunking (whole note, MiniLM) | 0.880 | [`eval/results/summary.md`](eval/results/summary.md) |
| Recall@5 on tail queries, whole note → chunks | 0.750 → 1.000 | [`eval/results/summary.md`](eval/results/summary.md) |
| Eval notes over MiniLM's 128-token limit | 80 of 80 | [`eval/results/summary.md`](eval/results/summary.md) |
| False positive rate at the 0.55 cut | 10% (1 of 10) | [`eval/results/summary.md`](eval/results/summary.md) |
| Recall@5 counting only notes above 0.55 | 0.740 | [`eval/results/summary.md`](eval/results/summary.md) |
| Agent cites the right note, 25 paraphrase/English queries (old cut rule → hint rule) | 76% → 96% | [`eval/results/agent/summary.md`](eval/results/agent/summary.md) |
| Agent cites a note on no-answer queries | 0 of 10 | [`eval/results/agent/summary.md`](eval/results/agent/summary.md) |
| Query latency p50 / p95, production (CPU) | 10.6 / 13.1 ms | [`eval/results/summary.md`](eval/results/summary.md) |
| Eval set | 80 notes, 60 queries (25 literal, 15 paraphrase, 10 cross-lingual, 10 no-answer) | [`eval/manifest.json`](eval/manifest.json) |
| Configs compared | 12 (3 models × whole/chunk × with/without title) | [`eval/results/`](eval/results/) |
| CI gate | Recall@5 ≥ 0.8 on 10 queries (currently 0.9) | [`Makefile`](Makefile), [`eval/run_eval.py`](eval/run_eval.py) |

## Architecture

![Architecture diagram. A Telegram message goes through bot.py to a headless Claude Code agent, which can also run in the terminal. The agent always searches first with embed.py search, which returns the top 5 and treats the score as a hint, flagging results below 0.55. embed.py embeds the query with MiniLM on CPU and reads title-prefixed chunks from ChromaDB. The agent opens a note with Read before citing it, and when asked it writes a note to the vault and indexes it with embed.py add. The eval harness reuses the same functions with a temporary Chroma for retrieval, runs the real agent with an Opus judge for answers, and CI runs a 10-query gate](docs/img/arquitetura.png)

- `embed.py` parses the frontmatter, drops the `## Links` section, packs whole paragraphs into chunks of up to 128 tokens with the title in front, and stores one vector per chunk (`<note_id>#<n>`). A note's score is its best chunk's score, and each note shows up once in the results.
- The agent follows [`CLAUDE.md`](CLAUDE.md). It runs `embed.py search` before answering a knowledge question, judges the 5 results by excerpt (the score is a hint), opens a note before using it, cites what it used, and only writes a note (following [`SCHEMA.md`](SCHEMA.md)) when asked.
- `bot.py` forwards Telegram messages to `claude -p` in the project directory and sends the answer back.
- Every CLI search appends a JSON line to `logs/search.jsonl` (query, note ids and scores, how many passed the cut, latency, model). `logs/` is gitignored.

## Decisions and trade-offs

### MiniLM with chunks, not bge-m3

bge-m3-chunk-notitle has the best nDCG@5 in the table (0.850 against 0.832) and a better Recall@1 (0.840 against 0.720), but a lower Recall@5 (0.920 against 0.960). What decided it was how search runs. Every `embed.py search` the agent makes is a new process that loads the model from disk, and bge-m3 is most of the ~2.5 GB that `make eval` downloads (comment in the [`Makefile`](Makefile)). In the eval run, with the files already in the OS cache, loading bge-m3 took 1.5 s against 0.6 s for MiniLM (`timing.model_load_s` in the results JSON), a query took about 80 ms against 10.6 ms, and indexing the 80 notes took 116 to 124 s against 12.8 s. For a CLI called once per question I kept the small model and fixed its 128-token limit with chunking.

### Not e5-small

I used the `query: ` and `passage: ` prefixes it was trained with, and it still compresses scores near the top. In every e5 config the lowest top-1 score among the no-answer queries is above 0.79, so FP@0.55 is 100%, and the cut it would need (0.90) keeps Recall@5 between 0.260 and 0.400.

### Title in front of every chunk

With MiniLM, chunks with and without the title tie on Recall@5 (0.960). The version with the title has a better nDCG@5 (0.832 against 0.813) and half the false positive rate at 0.55 (10% against 20%).

### A cut, and still showing what falls under it

Search prints 5 results and marks the ones under 0.55, so a person reading the output still sees them. The agent used to skip them. Since the [answer evaluation](#answer-evaluation) it reads the mark as a hint and judges each note by its excerpt, which took citing the right note from 76% to 96% with no false positives. The cut is configurable (`DENNOU_SCORE_THRESHOLD`) because it only holds for this model and chunking. If either changes, `make eval` has to run again.

### `sync` rebuilds into a staging collection

It builds a new collection and swaps it in at the end, so deleted notes drop out and an index in the old one-vector-per-note format gets migrated. `search` and `add` warn when they find the old format.

## Bugs worth telling

### Silent truncation at 128 tokens

Nothing in the old code looked wrong. Notes were embedded whole, search returned plausible results, and the tokenizer dropped everything past token 128 without a warning. The eval made it visible because I wrote long notes on purpose, with the answer only in the last part, and the whole-note config missed 3 of those 12 queries (tail Recall@5 0.750). Chunking took it to 1.000 ([`fc4dc1c`](https://github.com/romualdobarbosa/dennou/commit/fc4dc1c)).

### The Telegram bot answered without looking at the vault

The bot runs `claude -p` with `--allowedTools`, and a headless agent can't ask for permission, so anything off the list is denied. The list had `Bash(python3 embed.py:*)`, while `CLAUDE.md` tells the agent to run `.venv/bin/python3 embed.py search ...`. The rule matches by prefix, so the search was denied and the agent answered from general knowledge, as if the vault had nothing on the subject. I reproduced it with `claude -p` on a clean clone (denied before the fix, allowed and answered from the note after) and fixed the rule ([`8bae299`](https://github.com/romualdobarbosa/dennou/commit/8bae299)).

### The file tools had no path limit

The same list also let `Read`, `Write`, `Edit`, `Glob` and `Grep` run with no path pattern. I tested it on a clone with a fake token, and the headless agent read `.env`, read and wrote a file outside the repo and edited the README without a single denial. Now the session only gets `Bash`, `Read`, `Edit` and `Write`, it can write only inside `vault/`, and `.env` and `.bot_session` are denied. I ran the same prompts again and all of them were denied, while reading, creating and editing notes in the vault kept working.

## Limitations

- The eval is small and synthetic, written by the same person (plus an agent) who wrote the notes. See the caveats above.
- The answer evaluation is one run per query on a synthetic vault, where Sonnet already knows most answers, so "correct" can't tell versions apart. What it measures well is whether the agent uses the right note.
- No hybrid search (BM25) and no reranking in production (both tested, see above).
- There is no GIF or recorded demo of the Telegram bot.
- Notes created from the phone in Obsidian only get indexed when `embed.py add` (or `sync`) runs on the PC.
- The bot's agent can still read any file inside the repo that isn't a secret, because Claude Code allows reads in the working directory by default. Only `.env` and `.bot_session` are denied.
- On the five demo notes, "como criar uma branch no git" still puts `git commit` first and `git branch` second (output below). The eval measures 80 notes, not this case.

## How to run

### Quick path (sample notes, no setup of your own)

Requires [uv](https://docs.astral.sh/uv/).

```bash
make setup   # uv sync (creates .venv with Python 3.12) + generates TAGS.md
make demo    # indexes vault/examples into chroma_demo/ and runs one search
```

`make demo` indexes the five public notes in `vault/examples/` into a separate store, so it never mixes with your own notes. Real output:

~~~text
[0.6961] git commit (command) — 20260101000003-git-commit
  ## Exemplo ```bash git add src/main.py git commit -m "feat: adicionar endpoint de login" ```...
[0.6438] git branch (command) — 20260101000004-git-branch
  ## Flags úteis - `-d` — deleta só se o branch já foi mergeado - `-D` — deleta independente do estado - `-m <novo>` — renomear o branch atual ## Exemplo ```bash git branch feature/login git checkout fe...
[0.6432] git merge (command) — 20260101000005-git-merge
  ## Exemplo ```bash git checkout main git merge feature/login --no-ff -m "merge: integrar feature de login" ``` ## Gotchas - Conflitos precisam ser resolvidos manualmente — edite os arquivos marcados, ...
[0.1773] Dicionários em Python (syntax) — 20260101000002-dicionarios-python  (abaixo do corte 0.55)
  ## Exemplo ```python usuario = {"nome": "Ana", "idade": 30} usuario["email"] = "ana@exemplo.com" for chave, valor in usuario.items(): print(f"{chave}: {valor}") ```...
[0.0918] Listas em Python (syntax) — 20260101000001-listas-python  (abaixo do corte 0.55)
  ## O que é Estrutura de dados ordenada e mutável. Aceita elementos de tipos diferentes. ## Sintaxe ```python lista = [1, "dois", 3.0] lista.append(4) lista.remove("dois") lista[0] # acesso por índice ...
~~~

The deps (`torch` via `sentence-transformers`) lack wheels for very new Python releases, so the project pins 3.12. Run the scripts with `.venv/bin/python3`.

### Full path (your own vault, agent and bot)

1. Put your notes in `vault/` (format in [`SCHEMA.md`](SCHEMA.md)) and open `vault/` as an Obsidian vault. Notes in `vault/*.md` are gitignored.
2. Index them and search:
   ```bash
   .venv/bin/python3 embed.py sync                       # rebuild the whole index
   .venv/bin/python3 embed.py add vault/<note>.md        # index one note
   .venv/bin/python3 embed.py search "window functions"
   .venv/bin/python3 embed.py search "undo a commit" --type command --tag git -k 3
   ```
   Paths, model, cut and log can be changed with `DENNOU_VAULT_DIR`, `DENNOU_CHROMA_DIR`, `DENNOU_TAGS_FILE`, `DENNOU_MODEL`, `DENNOU_SCORE_THRESHOLD` and `DENNOU_LOG_FILE` (`off` disables the search log).
3. Talk to Claude Code in the repo. It searches before answering and saves a note when you ask ("salva isso", "cria uma nota", "anota aí").

If your `chroma_db/` was built by an older version (one vector per note, or with the `## Links` section embedded), run `embed.py sync` once.

#### Telegram bot

The bot forwards your message to the Claude Code agent in headless mode (`claude -p`), which follows the same `CLAUDE.md`, and replies back.

- Long polling with the standard library, so there is no public URL or webhook and it works behind a home router.
- It runs on the PC, so notes are saved locally.
- It only answers your `chat_id`, since it writes files and runs `embed.py` on the machine.
- The only shell command the headless agent may run is `.venv/bin/python3 embed.py`, it can only write inside `vault/`, and it can't read `.env` or anything outside the repo (`TOOLS`, `ALLOWED_TOOLS` and `DISALLOWED_TOOLS` in [`bot.py`](bot.py)).
- It keeps the conversation between messages (the session id lives in `.bot_session`), so "salva isso" sees the previous answer. `/novo` or `/reset` starts over.

To create your own bot:

1. In Telegram, talk to @BotFather (the verified one) and send `/newbot`. Pick a display name and a username ending in `bot`. BotFather replies with a token like `123456789:AA...`. Keep it secret.
2. `cp .env.example .env` and paste the token into `TELEGRAM_BOT_TOKEN`. Leave `TELEGRAM_OWNER_ID` empty for now (`DENNOU_BOT_MODEL` is optional and defaults to `sonnet`).
3. Send any message to your bot, then get your chat id:
   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" \
     | python3 -c "import sys,json; print(json.load(sys.stdin)['result'][-1]['message']['chat']['id'])"
   ```
   Put that number in `TELEGRAM_OWNER_ID`.
4. Run `.venv/bin/python3 bot.py`, ask a question, then say "salva isso".

The bot only replies after you message it, since Telegram doesn't let bots start a conversation. Messages from any other `chat_id` are rejected and logged as `[lock] chat_id não autorizado: <id>`.

#### Run the bot as a systemd user service

[`dennou-bot.service`](dennou-bot.service) uses `%h` (your home) and assumes the repo at `~/dennou`. Edit the `%h/dennou` paths if it lives elsewhere.

```bash
mkdir -p ~/.config/systemd/user
cp dennou-bot.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dennou-bot
journalctl --user -u dennou-bot -f      # logs
```

## Cost and security (who pays, who can use it)

The bot runs `claude -p` on the host machine with the owner's Claude authentication (the Claude Code login or API key on that machine). The Telegram user does not attach their own Claude account, and the API has no idea who is on the other end of the chat.

So whoever talks to the bot spends the owner's Claude plan and writes to the owner's vault, on the owner's machine. That is why the `TELEGRAM_OWNER_ID` lock exists. Without it, anyone who found the bot's username could burn your credits and touch your files (even with the tool rules, they could still read the repo and write to the vault).

There is no shared dennou bot. If someone else wants one, they run their own instance on their own machine, with their own Telegram token, their own `TELEGRAM_OWNER_ID` and their own Claude authentication. One instance per person and machine.

## Development

```bash
make lint         # ruff check + ruff format --check
make format       # ruff fix + format
make test         # pytest (embed index/search with a temp Chroma, frontmatter, bot with mocks, metrics)
make eval         # full retrieval eval
make eval-quick   # retrieval regression gate
```

`pre-commit install` sets up the ruff hooks from [`.pre-commit-config.yaml`](.pre-commit-config.yaml). [CI](.github/workflows/ci.yml) (GitHub Actions) runs `make lint`, `make test` and `make eval-quick` on every push to `main` and on pull requests. It installs the CPU build of torch, so it never downloads the CUDA libraries the lockfile pulls on Linux.

## Note types

| Type | Use |
|------|-----|
| `syntax` | Language syntax (Python, SQL, regex) |
| `concept` | Theory, explanation of a concept |
| `command` | Terminal commands, CLI tools |
| `error` | Bugs, debugging, fixes |
| `fact` | Facts, curiosities |
| `note` | Free-form notes |

## Structure

```
dennou/
├── vault/           # Markdown notes (Obsidian vault, gitignored except examples)
│   └── examples/    # public sample notes (used by make demo)
├── eval/            # retrieval eval: synthetic vault, queries, harness, results
├── tests/           # pytest
├── embed.py         # chunking, indexing and search
├── bot.py           # Telegram bot (headless agent bridge)
├── CLAUDE.md        # agent instructions
└── SCHEMA.md        # note schema and templates
```

## Stack

- RAG (retrieval-augmented generation) over a Zettelkasten-style Obsidian vault
- Vector Database (ChromaDB, local, cosine distance)
- Sentence Transformers (`paraphrase-multilingual-MiniLM-L12-v2`, local and multilingual, no embedding API)
- LLM Evaluation, specifically retrieval evaluation (Recall@k, MRR, nDCG, false positive rate at a threshold)
- Claude Code as the agent, interactive and headless (`claude -p`)
- Telegram Bot API (long polling, standard library only)
- CI/CD with GitHub Actions, uv, ruff, pytest, pre-commit
- Python 3.12

```
    ██████╗ ███████╗███╗   ██╗███╗   ██╗ ██████╗ ██╗   ██╗
    ██╔══██╗██╔════╝████╗  ██║████╗  ██║██╔═══██╗██║   ██║
    ██║  ██║█████╗  ██╔██╗ ██║██╔██╗ ██║██║   ██║██║   ██║
    ██║  ██║██╔══╝  ██║╚██╗██║██║╚██╗██║██║   ██║██║   ██║
    ██████╔╝███████╗██║ ╚████║██║ ╚████║╚██████╔╝╚██████╔╝
    ╚═════╝ ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝
      電脳 · cérebro eletrônico · RAG sobre Zettelkasten
```

MIT licensed, see [LICENSE](LICENSE).
