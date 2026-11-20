"""Eval de geração no modo agente: o dennou de verdade, com a regra antiga e a nova.

Uso (da raiz do repo):
    uv run python -m eval.run_agent_eval                    # 2 regras x 35 perguntas
    uv run python -m eval.run_agent_eval --rules pista --limit 3

Diferente do eval controlado (run_generation_eval), aqui ninguém monta o
prompt. Cada pergunta vira um `claude -p` igual ao do bot (mesmas ferramentas
e permissões), rodando numa cópia do projeto com o vault sintético de
eval/vault e o CLAUDE.md da regra testada:

- corte: a regra antiga, que manda ignorar as notas abaixo do corte 0.55;
- pista: a regra do CLAUDE.md atual, em que o score é pista e o agente julga
  pelo trecho e abre a nota com Read antes de usar.

O resto do CLAUDE.md é o mesmo nas duas.

Da transcrição (stream-json) saem as buscas que ele rodou, as notas que abriu
e a resposta final. A nota citada é achada no código, procurando título, nome
do arquivo ou id da nota na resposta (o CLAUDE.md manda citar o título no
fim). O juiz é o mesmo do eval controlado. Cada execução fica em cache em
eval/results/agent/runs.jsonl (fora do git: as transcrições têm caminhos locais).
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval import metrics as m
from eval import run_eval as r
from eval import run_generation_eval as g

OUT_DIR = r.RESULTS_DIR / "agent"
RUNS_FILE = OUT_DIR / "runs.jsonl"
# Fora do /tmp: lá o Claude Code não carrega o CLAUDE.md do diretório.
WORK_DIR = Path(
    os.environ.get("DENNOU_AGENT_EVAL_DIR", Path.home() / ".cache" / "dennou-agent-eval")
)

MODEL = "sonnet"  # o padrão do bot
KINDS = ("paraphrase", "cross_lingual", "no_answer")  # onde o corte pesa
TIMEOUT = 300

# Mesmas ferramentas e permissões do bot.py.
TOOLS = "Bash,Read,Edit,Write"
ALLOWED_TOOLS = [
    "Bash(.venv/bin/python3 embed.py:*)",
    "Read(./vault/**)",
    "Read(./SCHEMA.md)",
    "Read(./TAGS.md)",
    "Edit(./vault/**)",
]

# Regra antiga (até 20/11/2026), recolocada no lugar de NEW_RULE na variante "corte".
OLD_RULE = (
    "- Se encontrar notas relevantes (score ≥ 0.55), incorpore o conteúdo delas na resposta "
    "e mencione o título da nota ao final. O search mostra sempre as 5 melhores e marca com "
    '"(abaixo do corte 0.55)" as que não passam; ignore essas\n'
)
# Regra atual, igual à do CLAUDE.md.
NEW_RULE = (
    "- O search mostra as 5 notas mais parecidas, com score e trecho, e marca com "
    '"(abaixo do corte 0.55)" as de score baixo. Use o score como pista, não como corte: '
    "o que decide é se a nota trata do que foi perguntado. Nota abaixo do corte às vezes "
    "responde, principalmente quando a pergunta usa outras palavras ou outra língua\n"
    "- Se o título ou o trecho de uma nota parecer responder a pergunta, abra o arquivo com "
    "Read e confira antes de usar. Não use nota que não trata do assunto, mesmo com score alto\n"
    "- Se encontrar notas relevantes, incorpore o conteúdo delas na resposta e mencione o "
    "título da nota ao final\n"
)
RULES = {"corte": "ignora notas abaixo de 0.55", "pista": "score como pista, abre a nota"}

_SEARCH_LINE = re.compile(
    r"^\[(\d+(?:\.\d+)?)\] .* — (\S+?)(?:\.md)?(  \(abaixo do corte [^)]*\))?\s*$", re.M
)


def claude_md(rule: str) -> str:
    text = (r.ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert NEW_RULE in text, "a regra do corte mudou no CLAUDE.md; atualize NEW_RULE"
    return text if rule == "pista" else text.replace(NEW_RULE, OLD_RULE)


# --------------------------------------------------------------------------- workspace


def build_workspace(rule: str) -> Path:
    """Cópia mínima do projeto: embed.py, CLAUDE.md da regra, SCHEMA, vault do eval."""
    ws = WORK_DIR / rule
    shared = WORK_DIR / "_index"
    if not (shared / "chroma_db").exists():
        print("== indexando eval/vault (uma vez)", flush=True)
        shared.mkdir(parents=True, exist_ok=True)
        env = {
            **os.environ,
            "DENNOU_VAULT_DIR": str(r.VAULT_DIR),
            "DENNOU_CHROMA_DIR": str(shared / "chroma_db"),
            "DENNOU_TAGS_FILE": str(shared / "TAGS.md"),
            "DENNOU_LOG_FILE": "off",
        }
        subprocess.run(
            [sys.executable, str(r.ROOT / "embed.py"), "sync"],
            env=env, check=True, capture_output=True,
        )  # fmt: skip
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    shutil.copytree(r.VAULT_DIR, ws / "vault")
    shutil.copytree(shared / "chroma_db", ws / "chroma_db")
    shutil.copy(shared / "TAGS.md", ws / "TAGS.md")
    for name in ("embed.py", "SCHEMA.md"):
        shutil.copy(r.ROOT / name, ws / name)
    (ws / ".venv").symlink_to(r.ROOT / ".venv")
    (ws / "CLAUDE.md").write_text(claude_md(rule), encoding="utf-8")
    return ws


# --------------------------------------------------------------------------- transcrição


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).split())


def parse_transcript(lines: list[str]) -> dict:
    searches, reads, other_tools, result = [], [], [], {}
    pending: dict[str, dict] = {}
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
        msg = ev.get("message") or {}
        for block in msg.get("content") or [] if isinstance(msg, dict) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name, inp = block.get("name"), block.get("input") or {}
                if name == "Bash" and "embed.py search" in inp.get("command", ""):
                    item = {"command": inp["command"], "hits": []}
                    searches.append(item)
                    pending[block["id"]] = item
                elif name == "Read":
                    reads.append(inp.get("file_path", ""))
                else:
                    other_tools.append({"name": name, "input": inp})
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                content = block.get("content")
                if isinstance(content, list):
                    content = "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
                pending[block["tool_use_id"]]["hits"] = [
                    {"score": float(s), "file": f, "below": bool(b)}
                    for s, f, b in _SEARCH_LINE.findall(content or "")
                ]
    return {
        "searches": searches,
        "reads": reads,
        "other_tools": other_tools,
        "answer": result.get("result", ""),
        "is_error": bool(result.get("is_error")) or not result,
        "cost_usd": result.get("total_cost_usd"),
        "duration_ms": result.get("duration_ms"),
        "num_turns": result.get("num_turns"),
    }


def cited_notes(answer: str, notes: dict, candidates: set[str]) -> list[str]:
    """Notas que a resposta cita: título, nome do arquivo ou id aparecem no texto.

    Só conta nota que o agente viu (na busca ou abrindo o arquivo); sem isso,
    "git reflog" numa resposta de conhecimento geral casaria com a nota Git reflog.
    """
    text = norm(answer)
    out = []
    for nid, note in notes.items():
        if nid not in candidates:
            continue
        keys = [norm(note["title"]), nid, note["filename"]]
        if any(k in text for k in keys):
            out.append(nid)
    return out


# --------------------------------------------------------------------------- execução


_lock = threading.Lock()


def load_cache() -> dict:
    cache = {}
    if RUNS_FILE.exists():
        for line in RUNS_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                cache[row["key"]] = row
    return cache


def run_agent(ws: Path, rule: str, question: str, cache: dict) -> dict:
    key = hashlib.sha256(
        json.dumps([MODEL, claude_md(rule), question, ALLOWED_TOOLS]).encode()
    ).hexdigest()
    if key in cache:
        return cache[key]
    cmd = [
        "claude", "-p", question,
        "--model", MODEL,
        "--tools", TOOLS,
        "--allowedTools", *ALLOWED_TOOLS,
        "--no-session-persistence",
        "--output-format", "stream-json", "--verbose",
    ]  # fmt: skip
    env = {**os.environ, "DENNOU_LOG_FILE": "off"}
    for attempt in range(3):
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd, cwd=ws, env=env, capture_output=True, text=True, timeout=TIMEOUT
            )
            lines = proc.stdout.splitlines()
        except subprocess.TimeoutExpired as e:
            lines = (e.stdout or b"").decode(errors="replace").splitlines()
        parsed = parse_transcript(lines)
        parsed["wall_ms"] = round((time.perf_counter() - t0) * 1000)
        if not parsed["is_error"]:
            break
        print(f"  retry {attempt + 1} ({rule}): {parsed['answer'][:200]}", flush=True)
    else:
        raise RuntimeError(f"claude -p falhou 3 vezes: {question}")
    row = {"key": key, "rule": rule, "question": question, **parsed, "transcript": lines}
    with _lock:
        cache[key] = row
        with RUNS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def run_case(q, rule, ws, notes, file_to_id, gcache, acache) -> dict:
    run = run_agent(ws, rule, q["query"], acache)
    run = {**run, **parse_transcript(run["transcript"])}  # parser atual, mesmo em cache
    hits = [h for s in run["searches"] for h in s["hits"]]
    seen = {file_to_id.get(h["file"]) for h in hits} - {None}
    below = {file_to_id.get(h["file"]) for h in hits if h["below"]} - {None}
    read_ids = [file_to_id.get(Path(p).stem) for p in run["reads"]]
    read_ids = [i for i in dict.fromkeys(read_ids) if i]
    cited = cited_notes(run["answer"], notes, seen | set(read_ids))
    ans = {"answer": run["answer"], "used_note_ids": cited}
    judge = g.judge_prompt(q, ans, notes)
    j = g.call_claude(g.JUDGE_MODEL, g.JUDGE_SYSTEM, judge, g.JUDGE_SCHEMA, gcache)
    grade2 = {n for n, gr in q["relevant"].items() if gr >= m.ANSWER}
    return {
        "id": q["id"],
        "kind": q["kind"],
        "rule": rule,
        "n_searches": len(run["searches"]),
        "seen_grade2": bool(grade2 & seen),
        "grade2_only_below": bool(grade2 & seen) and not (grade2 & (seen - below)),
        "read": read_ids,
        "read_below": [i for i in read_ids if i in below],
        "cited": cited,
        "cited_grade2": bool(grade2 & set(cited)),
        "cited_any": bool(cited),
        "cited_irrelevant": [n for n in cited if q["relevant"].get(n, 0) == 0],
        "correct": j["output"]["correct"],
        "faithful": j["output"]["faithful"],
        "judge_reason": j["output"]["reason"],
        "answer": run["answer"],
        "other_tools": [t["name"] for t in run["other_tools"]],
        "num_turns": run["num_turns"],
        "wall_s": round(run["wall_ms"] / 1000, 1),
        "cost_usd": (run["cost_usd"] or 0) + (j["cost_usd"] or 0),
    }


def summarize(rows: list[dict]) -> dict:
    ans = [x for x in rows if x["kind"] != "no_answer"]
    no = [x for x in rows if x["kind"] == "no_answer"]
    hard = [x for x in ans if x["grade2_only_below"]]

    def rate(xs, key):
        return round(m.mean([1.0 if x[key] else 0.0 for x in xs]), 4) if xs else None

    return {
        "answerable": {
            "n": len(ans),
            "seen_grade2": rate(ans, "seen_grade2"),
            "cited_grade2": rate(ans, "cited_grade2"),
            "cited_irrelevant": rate(ans, "cited_irrelevant"),
            "correct": rate(ans, "correct"),
            "only_below": {"n": len(hard), "cited_grade2": rate(hard, "cited_grade2")},
            "by_kind": {
                k: {"n": len(xs), "cited_grade2": rate(xs, "cited_grade2")}
                for k in KINDS
                if k != "no_answer" and (xs := [x for x in ans if x["kind"] == k])
            },
        },
        "no_answer": {"n": len(no), "false_grounding": rate(no, "cited_any")},
        "faithful_all": rate(rows, "faithful"),
        "searched": rate(rows, "n_searches"),
        "reads_mean": round(m.mean([len(x["read"]) for x in rows]), 2),
        "read_below_rate": rate(rows, "read_below"),
        "wall_s_mean": round(m.mean([x["wall_s"] for x in rows]), 1),
        "cost_usd_total": round(sum(x["cost_usd"] for x in rows), 4),
    }


def pct(x) -> str:
    return "-" if x is None else f"{x:.0%}"


def write_report(summary: dict, rows: list[dict], meta: dict, path: Path) -> None:
    lines = [
        "# Eval de geração, modo agente",
        "",
        f"Gerado por `python -m eval.run_agent_eval` em {meta['date'][:10]} "
        f"(commit `{meta['commit']}`). Cada pergunta roda o `claude -p` do bot "
        f"(`{MODEL}`, mesmas ferramentas e permissões) numa cópia do projeto com "
        f"o vault de `eval/vault`. Juiz: `{g.JUDGE_MODEL}`. Uma rodada por pergunta; "
        f"perguntas dos tipos {', '.join(KINDS)}.",
        "",
        "| regra | buscou no vault | nota certa apareceu na busca | citou nota certa | "
        "só abaixo do corte: citou | citou nota irrelevante | fiel | FP sem resposta "
        "| notas abertas (média) | abriu nota abaixo do corte | tempo médio |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rule, s in summary.items():
        a, n = s["answerable"], s["no_answer"]
        ob = a["only_below"]
        ob_txt = f"{pct(ob['cited_grade2'])} ({ob['n']})" if ob["n"] else "-"
        lines.append(
            f"| {rule}: {RULES[rule]} | {pct(s['searched'])} | {pct(a['seen_grade2'])} "
            f"| {pct(a['cited_grade2'])} "
            f"| {ob_txt} | {pct(a['cited_irrelevant'])} | {pct(s['faithful_all'])} "
            f"| {pct(n['false_grounding'])} ({n['n']}) | {s['reads_mean']:.1f} "
            f"| {pct(s['read_below_rate'])} | {s['wall_s_mean']:.0f} s |"
        )
    lines += [
        "",
        '"Só abaixo do corte" = perguntas em que a nota certa veio na busca, mas só '
        "com score < 0.55 (são as que a regra atual manda ignorar).",
        "",
        "## Por kind (citou nota certa)",
        "",
        "| regra | " + " | ".join(k for k in KINDS if k != "no_answer") + " |",
        "|---|---|---|",
    ]
    for rule, s in summary.items():
        bk = s["answerable"]["by_kind"]
        lines.append(
            f"| {rule} | " + " | ".join(f"{pct(bk[k]['cited_grade2'])}" for k in bk) + " |"
        )
    lines += ["", "## Casos em que as regras discordam", ""]
    by_id: dict[str, dict] = {}
    for x in rows:
        by_id.setdefault(x["id"], {})[x["rule"]] = x
    for qid, vs in sorted(by_id.items()):
        keys = {(x["cited_grade2"], x["cited_any"], x["faithful"]) for x in vs.values()}
        if len(keys) > 1:
            parts = [
                f"{rule}: abriu {', '.join(x['read']) or 'nada'}, citou "
                f"{', '.join(x['cited']) or 'nada'}{'' if x['faithful'] else ' (infiel)'}"
                for rule, x in sorted(vs.items())
            ]
            lines.append(f"- **{qid}** ({next(iter(vs.values()))['kind']}): " + "; ".join(parts))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--rules", nargs="+", choices=list(RULES), default=list(RULES))
    ap.add_argument("--limit", type=int, default=None, help="só as N primeiras perguntas")
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    notes_list = r.load_notes()
    notes = {n["id"]: n for n in notes_list}
    file_to_id = {n["filename"]: n["id"] for n in notes_list}
    queries = [q for q in r.load_queries() if q["kind"] in KINDS]
    if args.limit:
        queries = queries[: args.limit]
    env = r.environment("cpu")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    workspaces = {rule: build_workspace(rule) for rule in args.rules}
    acache, gcache = load_cache(), g.load_cache()
    g.OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [(q, rule) for q in queries for rule in args.rules]
    print(f"== {len(jobs)} execuções ({len(acache)} em cache)", flush=True)
    done = [0]

    def work(job):
        q, rule = job
        row = run_case(q, rule, workspaces[rule], notes, file_to_id, gcache, acache)
        with _lock:
            done[0] += 1
            cited = ", ".join(row["cited"]) or "-"
            print(f"   {done[0]}/{len(jobs)} {q['id']} {rule}: citou {cited}", flush=True)
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(work, jobs))

    summary = {rule: summarize([x for x in rows if x["rule"] == rule]) for rule in args.rules}
    meta = {
        "date": env["date"],
        "commit": env["commit"],
        "model": MODEL,
        "judge_model": g.JUDGE_MODEL,
        "rules": {rule: RULES[rule] for rule in args.rules},
        "new_rule": NEW_RULE,
        "kinds": KINDS,
        "queries": len(queries),
    }
    # As respostas às vezes citam caminhos locais; o arquivo commitado não leva a home.
    payload = {"meta": meta, "summary": summary, "rows": rows}
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    (OUT_DIR / "results.json").write_text(
        text.replace(str(Path.home()), "~") + "\n", encoding="utf-8"
    )
    write_report(summary, rows, meta, OUT_DIR / "summary.md")
    for rule, s in summary.items():
        a, n = s["answerable"], s["no_answer"]
        print(
            f"{rule}: citou certa {pct(a['cited_grade2'])}  FP {pct(n['false_grounding'])}  "
            f"fiel {pct(s['faithful_all'])}  abertas {s['reads_mean']}  "
            f"tempo {s['wall_s_mean']} s  custo ${s['cost_usd_total']:.2f}"
        )
    print(f"resultados em {OUT_DIR.relative_to(r.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
