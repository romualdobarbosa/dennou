"""Eval de geração do dennou: a regra do corte muda a resposta do agente?

Uso (da raiz do repo):
    uv run python -m eval.run_generation_eval                 # 3 variantes x 60 perguntas
    uv run python -m eval.run_generation_eval --variants A --limit 5

Modo controlado: a busca roda aqui (config de produção, mesmo código do
eval de retrieval) e as notas que a variante deixa passar vão inteiras no
prompt. O modelo responde via `claude -p` sem ferramentas e sem CLAUDE.md,
devolvendo a resposta e os ids das notas que usou. Variantes:

- A: hoje, só notas com score >= 0.55;
- B: >= 0.55, mais uma faixa "talvez" de 0.45 a 0.55;
- C: top-5 inteiro com o score, o modelo decide.

Avaliação: por código, se citou nota de grau 2 (perguntas com resposta) ou
alguma nota (sem resposta, é falso positivo); e um juiz (outro `claude -p`)
dá correto/fiel pela rubrica de JUDGE_SYSTEM. Cada chamada fica em cache em
eval/results/generation/calls.jsonl (fora do git), então rodar de novo só faz o que falta.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from eval import metrics as m
from eval import run_eval as r

OUT_DIR = r.RESULTS_DIR / "generation"
CALLS_FILE = OUT_DIR / "calls.jsonl"

ANSWER_MODEL = "sonnet"  # o padrão do bot (DENNOU_BOT_MODEL)
JUDGE_MODEL = "opus"
CUT = r.PRODUCTION_THRESHOLD
MAYBE_CUT = 0.45
TOP_K = 5

VARIANTS = {
    "A": "só notas com score >= 0.55 (hoje)",
    "B": "notas >= 0.55 + faixa 'talvez' de 0.45 a 0.55",
    "C": "top-5 inteiro com score, o modelo decide",
}

ANSWER_SYSTEM = """\
Você é o assistente de uma base de conhecimento pessoal (notas em Markdown).
Antes de você responder, uma busca semântica no vault já rodou e as notas que
ela trouxe estão na mensagem do usuário, cada uma com id, título e texto.

- Se alguma nota responde a pergunta, responda usando o conteúdo dela e liste
  o id em used_note_ids. Liste só as notas que você de fato usou.
- Se nenhuma nota responde (ou não veio nenhuma), responda normalmente com o
  seu conhecimento e deixe used_note_ids vazio. Não force uma nota que não
  trata do assunto.
- Seja conciso. Responda em português."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "used_note_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "used_note_ids"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """\
Você avalia respostas de um assistente de base de conhecimento pessoal.
Recebe a pergunta, as notas de referência (as que respondem a pergunta, se
houver), as notas que o assistente citou e a resposta. Julgue:

- correct: a resposta acerta o que a pergunta pede. Com notas de referência,
  compare com elas; sem referência, a pergunta não tem resposta no vault e
  correct é true se a resposta não apresenta nenhuma nota como fonte da
  resposta (responder com conhecimento geral é aceitável).
- faithful: tudo que a resposta atribui às notas citadas está nelas e não
  contradiz o texto delas. Sem nota citada, faithful é true.

Seja estrito com fatos técnicos (flags, comandos, nomes, valores padrão).
Explique em uma frase em reason."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "correct": {"type": "boolean"},
        "faithful": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["correct", "faithful", "reason"],
    "additionalProperties": False,
}


# --------------------------------------------------------------------------- prompt


def shown_notes(variant: str, ranked: list[str], scores: dict[str, float]) -> list[dict]:
    """Notas do top-5 que a variante mostra ao modelo, com o rótulo de cada uma."""
    out = []
    for nid in ranked[:TOP_K]:
        s = scores[nid]
        if variant == "A" and s >= CUT:
            out.append({"id": nid, "score": s, "label": "relevante"})
        elif variant == "B" and s >= MAYBE_CUT:
            out.append({"id": nid, "score": s, "label": "relevante" if s >= CUT else "talvez"})
        elif variant == "C":
            out.append({"id": nid, "score": s, "label": None})
    return out


def note_block(note: dict, item: dict, variant: str) -> str:
    head = f"### [{note['id']}] {note['title']}"
    if variant == "C":
        head += f" (score {item['score']:.2f})"
    elif item["label"] == "talvez":
        head += " (talvez relevante: abaixo do corte, use só se responder de fato)"
    return f"{head}\n\n{r.embed.note_text(note, True, False)}"


def answer_prompt(question: str, variant: str, shown: list[dict], notes: dict) -> str:
    if not shown:
        return f"Pergunta: {question}\n\nA busca não trouxe nenhuma nota relevante."
    intro = {
        "A": "Notas que a busca considerou relevantes:",
        "B": "Notas que a busca trouxe (as marcadas 'talvez' ficaram abaixo do corte):",
        "C": "As 5 notas mais parecidas com a pergunta, com o score da busca (0 a 1):",
    }[variant]
    blocks = "\n\n".join(note_block(notes[i["id"]], i, variant) for i in shown)
    return f"Pergunta: {question}\n\n{intro}\n\n{blocks}"


def judge_prompt(q: dict, ans: dict, notes: dict) -> str:
    refs = [n for n, g in q["relevant"].items() if g >= m.ANSWER]
    ref_txt = (
        "\n\n".join(f"### [{n}]\n\n{r.embed.note_text(notes[n], True, False)}" for n in refs)
        or "(nenhuma: o vault não tem resposta pra essa pergunta)"
    )
    cited = [n for n in ans["used_note_ids"] if n in notes]
    cited_txt = (
        "\n\n".join(f"### [{n}]\n\n{r.embed.note_text(notes[n], True, False)}" for n in cited)
        or "(nenhuma)"
    )
    return (
        f"Pergunta: {q['query']}\n\n## Notas de referência\n\n{ref_txt}\n\n"
        f"## Notas citadas pelo assistente\n\n{cited_txt}\n\n"
        f"## Resposta do assistente\n\n{ans['answer']}"
    )


# --------------------------------------------------------------------------- claude -p


_lock = threading.Lock()


def load_cache() -> dict:
    cache = {}
    if CALLS_FILE.exists():
        for line in CALLS_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                cache[row["key"]] = row
    return cache


def call_claude(model: str, system: str, prompt: str, schema: dict, cache: dict) -> dict:
    """Roda `claude -p` sem ferramentas, sem CLAUDE.md nem settings; usa o cache."""
    key = hashlib.sha256(
        json.dumps([model, system, prompt, schema], ensure_ascii=False).encode()
    ).hexdigest()
    if key in cache:
        return cache[key]
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--system-prompt", system,
        "--json-schema", json.dumps(schema),
        "--tools", "",
        "--setting-sources", "",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--output-format", "json",
    ]  # fmt: skip
    for attempt in range(3):
        # Diretório vazio: nenhum CLAUDE.md do projeto é descoberto.
        with tempfile.TemporaryDirectory(prefix="dennou-gen-") as tmp:
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=600)
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            data = {"is_error": True, "result": proc.stdout[-500:] + proc.stderr[-500:]}
        if not data.get("is_error") and data.get("structured_output") is not None:
            break
        print(f"  retry {attempt + 1}: {str(data.get('result'))[:200]}", flush=True)
    else:
        raise RuntimeError(f"claude -p falhou 3 vezes: {data.get('result')}")
    row = {
        "key": key,
        "model": next(iter(data.get("modelUsage") or {}), model),
        "output": data["structured_output"],
        "cost_usd": data.get("total_cost_usd"),
        "duration_ms": data.get("duration_ms"),
    }
    with _lock:
        cache[key] = row
        with CALLS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


# --------------------------------------------------------------------------- execução


def run_case(q, pq, variant, notes, cache) -> dict:
    shown = shown_notes(variant, pq["ranked"], pq["scores"])
    prompt = answer_prompt(q["query"], variant, shown, notes)
    a = call_claude(ANSWER_MODEL, ANSWER_SYSTEM, prompt, ANSWER_SCHEMA, cache)
    ans = a["output"]
    j = call_claude(JUDGE_MODEL, JUDGE_SYSTEM, judge_prompt(q, ans, notes), JUDGE_SCHEMA, cache)
    cited = list(dict.fromkeys(ans["used_note_ids"]))
    grade2 = {n for n, g in q["relevant"].items() if g >= m.ANSWER}
    return {
        "id": q["id"],
        "kind": q["kind"],
        "variant": variant,
        "shown": [
            {"id": s["id"], "score": round(s["score"], 4), "label": s["label"]} for s in shown
        ],
        "shown_grade2": bool(grade2 & {s["id"] for s in shown}),
        "prompt_chars": len(prompt),
        "answer": ans["answer"],
        "cited": cited,
        "cited_unknown": [n for n in cited if n not in notes],
        "cited_grade2": bool(grade2 & set(cited)),
        "cited_any": bool(cited),
        "cited_irrelevant": [n for n in cited if q["relevant"].get(n, 0) == 0],
        "correct": j["output"]["correct"],
        "faithful": j["output"]["faithful"],
        "judge_reason": j["output"]["reason"],
        "answer_model": a["model"],
        "judge_model": j["model"],
        "cost_usd": (a["cost_usd"] or 0) + (j["cost_usd"] or 0),
    }


def summarize(rows: list[dict]) -> dict:
    ans = [x for x in rows if x["kind"] != "no_answer"]
    no = [x for x in rows if x["kind"] == "no_answer"]

    def rate(xs, key):
        return round(m.mean([1.0 if x[key] else 0.0 for x in xs]), 4)

    return {
        "answerable": {
            "n": len(ans),
            "shown_grade2": rate(ans, "shown_grade2"),
            "cited_grade2": rate(ans, "cited_grade2"),
            "cited_irrelevant": rate(ans, "cited_irrelevant"),
            "correct": rate(ans, "correct"),
            "faithful": rate(ans, "faithful"),
            "by_kind": {
                k: {
                    "n": len(xs),
                    "cited_grade2": rate(xs, "cited_grade2"),
                    "correct": rate(xs, "correct"),
                }
                for k in ("literal", "paraphrase", "cross_lingual")
                if (xs := [x for x in ans if x["kind"] == k])
            },
        },
        "no_answer": {
            "n": len(no),
            "false_grounding": rate(no, "cited_any"),
            "correct": rate(no, "correct"),
        },
        "faithful_all": rate(rows, "faithful"),
        "prompt_chars_mean": round(m.mean([x["prompt_chars"] for x in rows]), 1),
        "cost_usd_total": round(sum(x["cost_usd"] for x in rows), 4),
    }


def write_report(summary: dict, rows: list[dict], meta: dict, path: Path) -> None:
    lines = [
        "# Eval de geração",
        "",
        f"Gerado por `python -m eval.run_generation_eval` em {meta['date'][:10]} "
        f"(commit `{meta['commit']}`). Busca: `{r.PRODUCTION_CONFIG}` no vault de "
        f"`eval/vault`. Resposta: `{meta['answer_model']}` via `claude -p` sem ferramentas; "
        f"juiz: `{meta['judge_model']}`. Uma rodada por pergunta.",
        "",
        "| variante | nota certa no prompt | citou nota certa | citou nota irrelevante "
        "| correta (juiz) | fiel (juiz) | FP sem resposta | prompt médio (chars) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for v, s in summary.items():
        a, n = s["answerable"], s["no_answer"]
        lines.append(
            f"| {v}: {VARIANTS[v]} | {a['shown_grade2']:.0%} | {a['cited_grade2']:.0%} "
            f"| {a['cited_irrelevant']:.0%} | {a['correct']:.0%} | {s['faithful_all']:.0%} "
            f"| {n['false_grounding']:.0%} ({n['n']}) | {s['prompt_chars_mean']:.0f} |"
        )
    lines += [
        "",
        f"Perguntas com resposta: {summary[next(iter(summary))]['answerable']['n']}. "
        '"Citou nota certa" = o modelo listou uma nota de grau 2 em used_note_ids. '
        '"FP sem resposta" = nas perguntas sem resposta no vault, citou alguma nota. '
        '"Fiel" vale para as 60 perguntas.',
        "",
        "## Por kind (citou nota certa / correta)",
        "",
        "| variante | literal | paraphrase | cross_lingual |",
        "|---|---|---|---|",
    ]
    for v, s in summary.items():
        bk = s["answerable"]["by_kind"]
        cells = [f"{bk[k]['cited_grade2']:.0%} / {bk[k]['correct']:.0%}" for k in bk]
        lines.append(f"| {v} | " + " | ".join(cells) + " |")
    lines += ["", "## Casos em que as variantes discordam", ""]
    by_id: dict[str, dict] = {}
    for x in rows:
        by_id.setdefault(x["id"], {})[x["variant"]] = x
    for qid, vs in sorted(by_id.items()):
        keys = {(x["cited_grade2"], x["correct"], bool(x["cited_irrelevant"])) for x in vs.values()}
        if len(keys) > 1:
            parts = [
                f"{v}: citou {', '.join(x['cited']) or 'nada'}, "
                f"{'correta' if x['correct'] else 'errada'}"
                for v, x in sorted(vs.items())
            ]
            lines.append(f"- **{qid}** ({next(iter(vs.values()))['kind']}): " + "; ".join(parts))
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    ap.add_argument("--limit", type=int, default=None, help="só as N primeiras perguntas")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    notes_list, queries = r.load_notes(), r.load_queries()
    if args.limit:
        queries = queries[: args.limit]
    notes = {n["id"]: n for n in notes_list}
    manifest = json.loads(r.MANIFEST_FILE.read_text(encoding="utf-8"))
    env = r.environment("cpu")

    print(f"== busca ({r.PRODUCTION_CONFIG})", flush=True)
    _, per_query = r.run_config(
        r.parse_config(r.PRODUCTION_CONFIG), notes_list, queries, manifest, "cpu", {}
    )
    pq_by_id = {pq["query"]["id"]: pq for pq in per_query}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache = load_cache()
    jobs = [(q, pq_by_id[q["id"]], v) for v in args.variants for q in queries]
    print(f"== {len(jobs)} casos ({len(cache)} chamadas em cache)", flush=True)
    done = [0]

    def work(job):
        q, pq, v = job
        row = run_case(q, pq, v, notes, cache)
        with _lock:
            done[0] += 1
            if done[0] % 10 == 0 or done[0] == len(jobs):
                print(f"   {done[0]}/{len(jobs)}", flush=True)
        return row

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(work, jobs))

    summary = {v: summarize([x for x in rows if x["variant"] == v]) for v in args.variants}
    meta = {
        "date": env["date"],
        "commit": env["commit"],
        "answer_model": sorted({x["answer_model"] for x in rows}),
        "judge_model": sorted({x["judge_model"] for x in rows}),
        "cut": CUT,
        "maybe_cut": MAYBE_CUT,
        "variants": {v: VARIANTS[v] for v in args.variants},
        "answer_system": ANSWER_SYSTEM,
        "judge_system": JUDGE_SYSTEM,
        "queries": len(queries),
    }
    meta["answer_model"] = ", ".join(meta["answer_model"])
    meta["judge_model"] = ", ".join(meta["judge_model"])
    (OUT_DIR / "results.json").write_text(
        json.dumps({"meta": meta, "summary": summary, "rows": rows}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    write_report(summary, rows, meta, OUT_DIR / "summary.md")
    for v, s in summary.items():
        a, n = s["answerable"], s["no_answer"]
        print(
            f"{v}: citou certa {a['cited_grade2']:.0%}  correta {a['correct']:.0%}  "
            f"fiel {s['faithful_all']:.0%}  FP {n['false_grounding']:.0%}  "
            f"custo ${s['cost_usd_total']:.2f}"
        )
    print(f"resultados em {OUT_DIR.relative_to(r.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
