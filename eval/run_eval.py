"""Eval de retrieval do dennou sobre o vault sintético de eval/vault.

Uso (da raiz do repo):
    uv run python -m eval.run_eval                # todas as configs, grava em eval/results/
    uv run python -m eval.run_eval --configs minilm-whole-title
    uv run python -m eval.run_eval --quick --min-recall5 0.8   # gate do CI

Cada config indexa eval/vault num Chroma temporário (cosseno, igual à produção)
e roda as perguntas de eval/queries.jsonl. A config de produção
(minilm-whole-title) usa as mesmas funções do embed.py: mesmo parse da nota,
mesmo texto (título + corpo), mesmo modelo e mesma conversão distância -> score.
"""

import argparse
import json
import platform
import random
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import embed  # noqa: E402
from eval import metrics as m  # noqa: E402

EVAL_DIR = ROOT / "eval"
VAULT_DIR = EVAL_DIR / "vault"
QUERIES_FILE = EVAL_DIR / "queries.jsonl"
MANIFEST_FILE = EVAL_DIR / "manifest.json"
RESULTS_DIR = EVAL_DIR / "results"

MODELS = {
    "minilm": {
        "name": "paraphrase-multilingual-MiniLM-L12-v2",
        "query_prefix": "",
        "passage_prefix": "",
    },
    # O e5 foi treinado com esses prefixos; sem eles a comparação fica injusta.
    "e5-small": {
        "name": "intfloat/multilingual-e5-small",
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
    "bge-m3": {"name": "BAAI/bge-m3", "query_prefix": "", "passage_prefix": ""},
}
PRODUCTION_CONFIG = "minilm-whole-title"

# Chunks de até 256 tokens (ou o max_seq_length do modelo, se for menor),
# contando prefixo, título e tokens especiais. Assim nenhum chunk é truncado
# e o tamanho do chunk é o mesmo pros modelos que aceitam mais.
CHUNK_MAX_TOKENS = 256
# Sobreposição (em fração de palavras) só quando um parágrafo sozinho não cabe.
WORD_OVERLAP = 0.2

TOP_K = 5
MRR_DEPTH = 10
THRESHOLDS = [round(i * 0.05, 2) for i in range(21)]
PRODUCTION_THRESHOLD = 0.4
MAX_FP_RATE = 0.10

# Subconjunto fixo do eval-quick (gate do CI): perguntas com resposta, de todos
# os kinds com recall, nenhuma de cauda de nota longa. Escolhido antes de rodar.
QUICK_QUERIES = [
    "q001",
    "q003",
    "q007",
    "q009",
    "q016",
    "q026",
    "q030",
    "q035",
    "q042",
    "q050",
]

# Experimento do campo related.
RELATED_TOP_N = 3
RELATED_LAMBDAS = [0.8, 0.9, 1.0]


# --------------------------------------------------------------------------- dados


def load_notes() -> list[dict]:
    notes = []
    for path in sorted(VAULT_DIR.glob("*.md")):
        note = embed._parse_note(path)
        if note is None:
            raise ValueError(f"nota inválida: {path}")
        text = path.read_text(encoding="utf-8")
        related = []
        for line in text.splitlines():
            if line.startswith("related:"):
                raw = line.partition(":")[2].strip().strip("[]")
                related = [r.strip() for r in raw.split(",") if r.strip()]
                break
        note["related"] = related
        notes.append(note)
    return notes


def load_queries() -> list[dict]:
    with QUERIES_FILE.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def all_configs() -> list[str]:
    return [
        f"{model}-{mode}-{title}"
        for model in MODELS
        for mode in ("whole", "chunk")
        for title in ("title", "notitle")
    ]


def parse_config(name: str) -> dict:
    model, _, rest = name.partition("-whole-") if "-whole-" in name else name.partition("-chunk-")
    mode = "whole" if "-whole-" in name else "chunk"
    if model not in MODELS or rest not in ("title", "notitle"):
        raise ValueError(f"config desconhecida: {name} (use uma de {all_configs()})")
    return {"name": name, "model": model, "chunking": mode, "include_title": rest == "title"}


# --------------------------------------------------------------------------- chunking


def split_paragraphs(body: str) -> list[str]:
    """Separa por linha em branco, sem quebrar blocos de código cercados por ```."""
    paragraphs, current, in_fence = [], [], False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                paragraphs.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append("\n".join(current))
    return paragraphs


def chunk_body(body: str, fits) -> list[str]:
    """
    Agrupa parágrafos consecutivos enquanto o chunk couber (fits(texto) -> bool).
    Parágrafo que sozinho não cabe vira janelas de palavras com sobreposição.
    """
    chunks, current = [], ""
    for para in split_paragraphs(body):
        candidate = f"{current}\n\n{para}" if current else para
        if fits(candidate):
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if fits(para):
            current = para
            continue
        words, start = para.split(" "), 0
        while start < len(words):
            end = start + 1
            while end < len(words) and fits(" ".join(words[start : end + 1])):
                end += 1
            chunks.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start = max(start + 1, end - int((end - start) * WORD_OVERLAP))
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------- execução


def environment(device: str) -> dict:
    import chromadb
    import sentence_transformers
    import torch

    cpu = platform.processor() or ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.partition(":")[2].strip()
                break
    except OSError:
        pass
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "embed.py", "eval", ":!eval/results"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if dirty:
            commit += "-dirty"
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    return {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "commit": commit,
        "device": device,
        "cpu": cpu,
        "torch_threads": torch.get_num_threads(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "chromadb": chromadb.__version__,
    }


def seed_everything(seed: int = 0) -> None:
    import numpy as np
    import torch
    import transformers

    # Contar tokens de nota longa avisa "sequence length is longer"; é esperado aqui.
    transformers.logging.set_verbosity_error()

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def run_config(config: dict, notes, queries, manifest, device: str, model_cache: dict) -> dict:
    spec = MODELS[config["model"]]
    seed_everything()
    t0 = time.perf_counter()
    if spec["name"] not in model_cache:
        model_cache.clear()  # um modelo por vez na memória
        model_cache[spec["name"]] = embed.load_model(spec["name"], device=device)
    model = model_cache[spec["name"]]
    model_load_s = time.perf_counter() - t0
    max_seq = model.max_seq_length
    tok = model.tokenizer

    def n_tokens(text: str) -> int:
        return len(tok(text, add_special_tokens=True, truncation=False)["input_ids"])

    chunk_limit = min(CHUNK_MAX_TOKENS, max_seq)
    texts_by_note = {}
    truncated = []
    for note in notes:
        full = spec["passage_prefix"] + embed.note_text(note, config["include_title"])
        if n_tokens(full) > max_seq:
            truncated.append(note["id"])
        if config["chunking"] == "whole":
            texts_by_note[note["id"]] = [full]
        else:
            head = spec["passage_prefix"]
            if config["include_title"]:
                head += f"{note['title']}\n\n"
            chunks = chunk_body(note["body"], lambda t, h=head: n_tokens(h + t) <= chunk_limit)
            texts_by_note[note["id"]] = [head + c for c in chunks]

    with tempfile.TemporaryDirectory(prefix="dennou-eval-") as tmp:
        collection = embed.open_collection(tmp, name="eval")
        t0 = time.perf_counter()
        for note in notes:
            texts = texts_by_note[note["id"]]
            embs = model.encode(texts)
            collection.upsert(
                ids=[f"{note['id']}#{i}" for i in range(len(texts))],
                embeddings=[e.tolist() for e in embs],
                documents=texts,
                metadatas=[{"note_id": note["id"]} for _ in texts],
            )
        index_s = time.perf_counter() - t0
        n_items = collection.count()

        # Quantos itens a busca precisaria pedir pra devolver top-5 notas.
        fetch = TOP_K if config["chunking"] == "whole" else min(n_items, 50)
        model.encode(spec["query_prefix"] + "aquecimento")  # 1a chamada é mais lenta

        per_query, latencies = [], []
        for q in queries:
            t0 = time.perf_counter()
            q_emb = model.encode(spec["query_prefix"] + q["query"]).tolist()
            collection.query(query_embeddings=[q_emb], n_results=fetch, include=["distances"])
            latencies.append((time.perf_counter() - t0) * 1000)

            # Ranking completo (fora do tempo medido) pra métricas, threshold e related.
            res = collection.query(
                query_embeddings=[q_emb], n_results=n_items, include=["distances", "metadatas"]
            )
            scores = {}
            for meta, dist in zip(res["metadatas"][0], res["distances"][0], strict=True):
                s = embed.distance_to_score(dist)
                nid = meta["note_id"]
                scores[nid] = max(s, scores.get(nid, -1.0))
            ranked = sorted(scores, key=lambda n: (-scores[n], n))
            per_query.append({"query": q, "ranked": ranked, "scores": scores})

    result = summarize(config, per_query, manifest, latencies)
    result["meta"] = {
        "config": config["name"],
        "model": spec["name"],
        "query_prefix": spec["query_prefix"],
        "passage_prefix": spec["passage_prefix"],
        "max_seq_length": max_seq,
        "embedding_dim": model.get_embedding_dimension(),
        "include_title": config["include_title"],
        "chunking": {
            "mode": config["chunking"],
            "max_tokens": chunk_limit if config["chunking"] == "chunk" else None,
            "word_overlap": WORD_OVERLAP if config["chunking"] == "chunk" else None,
            "items_indexed": n_items,
        },
        "notes": len(notes),
        "notes_over_max_seq_length": len(truncated),
        "long_notes_over_max_seq_length": len(set(truncated) & set(manifest["long_notes"])),
        "vault": "eval/vault",
    }
    result["timing"].update(
        {"index_total_s": round(index_s, 3), "model_load_s": round(model_load_s, 3)}
    )
    return result, per_query


def query_metrics(ranked: list[str], relevant: dict[str, int]) -> dict:
    return {
        "recall@1": m.recall_at_k(ranked, relevant, 1),
        "recall@3": m.recall_at_k(ranked, relevant, 3),
        "recall@5": m.recall_at_k(ranked, relevant, 5),
        "rr": m.reciprocal_rank(ranked[:MRR_DEPTH], relevant),
        "ndcg@5": m.ndcg_at_k(ranked, relevant, 5),
    }


def aggregate(rows: list[dict]) -> dict:
    keys = ["recall@1", "recall@3", "recall@5", "rr", "ndcg@5"]
    out = {k if k != "rr" else "mrr": round(m.mean([r[k] for r in rows]), 4) for k in keys}
    out["n"] = len(rows)
    return out


def summarize(config, per_query, manifest, latencies) -> dict:
    tail = set(manifest["tail_answer_queries"])
    rows, details = [], []
    answerable, no_answer = [], []
    for pq in per_query:
        q, ranked, scores = pq["query"], pq["ranked"], pq["scores"]
        top = [{"id": n, "score": scores[n]} for n in ranked[:TOP_K]]
        if q["kind"] == "no_answer":
            no_answer.append((ranked, scores))
            details.append({"id": q["id"], "kind": q["kind"], "top5": top})
            continue
        qm = query_metrics(ranked, q["relevant"])
        rows.append({**qm, "kind": q["kind"], "id": q["id"]})
        answerable.append((ranked, scores, q["relevant"]))
        details.append({"id": q["id"], "kind": q["kind"], **qm, "top5": top})

    by_kind = {
        kind: aggregate([r for r in rows if r["kind"] == kind])
        for kind in ("literal", "paraphrase", "cross_lingual")
    }
    curve = m.threshold_curve(answerable, no_answer, THRESHOLDS, k=TOP_K)
    at_prod = next(c for c in curve if c["threshold"] == PRODUCTION_THRESHOLD)
    return {
        "metrics": {
            "overall": aggregate(rows),
            "by_kind": by_kind,
            "tail_answer": aggregate([r for r in rows if r["id"] in tail]),
            "no_answer_top1_score_mean": round(m.mean([s[r[0]] for r, s in no_answer]), 4),
        },
        "threshold": {
            "curve": curve,
            "at_production": at_prod,
            "suggested": m.suggest_threshold(curve, MAX_FP_RATE),
            "criterion": f"maior Recall@5 (só notas com score >= t) com FP <= {MAX_FP_RATE:.0%}",
        },
        "timing": {
            "query_p50_ms": round(m.percentile(latencies, 50), 2),
            "query_p95_ms": round(m.percentile(latencies, 95), 2),
        },
        "queries": details,
    }


# --------------------------------------------------------------------------- related


def related_experiment(per_query, notes, manifest) -> dict:
    """
    Expansão pelo campo related: cada nota relacionada a uma das top-N notas
    recebe score max(score próprio, λ * score da nota de origem) e a lista é
    reordenada. λ = 1 coloca a relacionada empatada com a origem (logo depois
    dela); λ < 1 só promove se a origem tiver score bem acima.
    """
    related = {n["id"]: n["related"] for n in notes}

    def expand(ranked, scores, lam):
        new = dict(scores)
        for parent in ranked[:RELATED_TOP_N]:
            for r in related.get(parent, []):
                new[r] = max(new.get(r, -1.0), lam * scores[parent])
        # Empate desfeito pela posição original: com λ = 1 a origem fica na frente.
        pos = {n: i for i, n in enumerate(ranked)}
        return sorted(new, key=lambda n: (-new[n], pos.get(n, len(pos))))

    def evaluate(rank_fn):
        rows = []
        for pq in per_query:
            q = pq["query"]
            if q["kind"] == "no_answer":
                continue
            ranked = rank_fn(pq["ranked"], pq["scores"])
            rows.append({**query_metrics(ranked, q["relevant"]), "kind": q["kind"], "id": q["id"]})
        tail = set(manifest["tail_answer_queries"])
        return {
            "overall": aggregate(rows),
            "by_kind": {
                k: aggregate([r for r in rows if r["kind"] == k])
                for k in ("literal", "paraphrase", "cross_lingual")
            },
            "tail_answer": aggregate([r for r in rows if r["id"] in tail]),
        }

    out = {"top_n": RELATED_TOP_N, "baseline": evaluate(lambda r, s: r), "expanded": {}}
    for lam in RELATED_LAMBDAS:
        out["expanded"][str(lam)] = evaluate(lambda r, s, lam=lam: expand(r, s, lam))
    return out


# --------------------------------------------------------------------------- relatório


def fmt(x: float) -> str:
    return f"{x:.3f}"


def write_summary(results: dict[str, dict], related: dict | None, path: Path) -> None:
    names = [n for n in all_configs() if n in results]
    first = results[names[0]]["meta"]
    env = first["env"]
    lines = [
        "# Resultados do eval de retrieval",
        "",
        f"Gerado por `make eval` em {env['date'][:10]} (commit `{env['commit']}`), "
        f"device `{env['device']}` ({env['cpu']}, {env['torch_threads']} threads, "
        f"torch {env['torch']}). Vault sintético de `eval/vault` (80 notas), 60 perguntas "
        f"(50 com resposta, 10 sem). `{PRODUCTION_CONFIG}` é a config de produção.",
        "",
        "## Geral (50 perguntas com resposta)",
        "",
        "| config | R@1 | R@3 | R@5 | MRR | nDCG@5 | FP@0.4 | R@5 com t=0.4 "
        "| t sugerido (R@5 / FP) | p50 ms | p95 ms | indexação s |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n in names:
        r = results[n]
        o, th, t = r["metrics"]["overall"], r["threshold"], r["timing"]
        sug = th["suggested"]
        sug_s = "—"
        if sug:
            sug_s = f"{sug['threshold']:.2f} ({fmt(sug['recall'])} / {sug['fp_rate']:.0%})"
        label = f"**{n}**" if n == PRODUCTION_CONFIG else n
        lines.append(
            f"| {label} | {fmt(o['recall@1'])} | {fmt(o['recall@3'])} | {fmt(o['recall@5'])} "
            f"| {fmt(o['mrr'])} | {fmt(o['ndcg@5'])} | {th['at_production']['fp_rate']:.0%} "
            f"| {fmt(th['at_production']['recall'])} | {sug_s} | {t['query_p50_ms']:.1f} "
            f"| {t['query_p95_ms']:.1f} | {t['index_total_s']:.1f} |"
        )
    lines += [
        "",
        "## Recall@5 por kind e nas perguntas de cauda",
        "",
        "Cauda = as 12 perguntas cuja resposta só aparece depois de ~400 palavras numa nota "
        "longa. A última coluna conta quantas notas passam do `max_seq_length` do modelo "
        "(o excesso é cortado sem aviso no modo nota inteira).",
        "",
        "| config | literal | paraphrase | cross_lingual | cauda | max_seq_length "
        "| notas truncadas |",
        "|---|---|---|---|---|---|---|",
    ]
    for n in names:
        r = results[n]
        bk, meta = r["metrics"]["by_kind"], r["meta"]
        trunc = meta["notes_over_max_seq_length"] if meta["chunking"]["mode"] == "whole" else 0
        lines.append(
            f"| {n} | {fmt(bk['literal']['recall@5'])} | {fmt(bk['paraphrase']['recall@5'])} "
            f"| {fmt(bk['cross_lingual']['recall@5'])} "
            f"| {fmt(r['metrics']['tail_answer']['recall@5'])} | {meta['max_seq_length']} "
            f"| {trunc} |"
        )
    if related:
        b = related["baseline"]
        lines += [
            "",
            f"## Expansão pelo campo related ({related['config']})",
            "",
            f"Notas relacionadas às top-{related['top_n']} entram com score "
            "max(próprio, λ × score da origem) e a lista é reordenada.",
            "",
            "| variante | R@5 | nDCG@5 | MRR | R@5 cauda |",
            "|---|---|---|---|---|",
            f"| sem expansão | {fmt(b['overall']['recall@5'])} | {fmt(b['overall']['ndcg@5'])} "
            f"| {fmt(b['overall']['mrr'])} | {fmt(b['tail_answer']['recall@5'])} |",
        ]
        for lam, e in related["expanded"].items():
            lines.append(
                f"| λ = {lam} | {fmt(e['overall']['recall@5'])} | {fmt(e['overall']['ndcg@5'])} "
                f"| {fmt(e['overall']['mrr'])} | {fmt(e['tail_answer']['recall@5'])} |"
            )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def best_config(results: dict[str, dict]) -> str:
    return max(
        results,
        key=lambda n: (
            results[n]["metrics"]["overall"]["ndcg@5"],
            results[n]["metrics"]["overall"]["recall@5"],
        ),
    )


# --------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--configs", nargs="+", default=None, help=f"default: {all_configs()}")
    ap.add_argument("--device", default="cpu", help="cpu (default), cuda, mps...")
    ap.add_argument("--out", type=Path, default=RESULTS_DIR)
    ap.add_argument("--quick", action="store_true", help="gate do CI: 10 perguntas, produção")
    ap.add_argument("--min-recall5", type=float, default=None, help="mínimo do --quick")
    ap.add_argument("--no-related", action="store_true", help="pula o experimento do related")
    args = ap.parse_args()

    notes, queries = load_notes(), load_queries()
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    env = environment(args.device)
    cache: dict = {}

    if args.quick:
        subset = [q for q in queries if q["id"] in QUICK_QUERIES]
        result, _ = run_config(
            parse_config(PRODUCTION_CONFIG), notes, subset, manifest, args.device, cache
        )
        r5 = result["metrics"]["overall"]["recall@5"]
        print(f"eval-quick ({PRODUCTION_CONFIG}, {len(subset)} perguntas): Recall@5 = {r5:.3f}")
        for d in result["queries"]:
            print(f"  {d['id']} recall@5={d['recall@5']:.0f} top1={d['top5'][0]['id']}")
        if args.min_recall5 is not None and r5 < args.min_recall5:
            print(f"FALHOU: Recall@5 {r5:.3f} < mínimo {args.min_recall5:.3f}")
            return 1
        return 0

    names = args.configs or all_configs()
    configs = [parse_config(n) for n in names]
    configs.sort(key=lambda c: list(MODELS).index(c["model"]))  # carrega cada modelo uma vez
    args.out.mkdir(parents=True, exist_ok=True)

    results, rankings = {}, {}
    for config in configs:
        print(f"== {config['name']}", flush=True)
        result, per_query = run_config(config, notes, queries, manifest, args.device, cache)
        result["meta"]["env"] = env
        results[config["name"]], rankings[config["name"]] = result, per_query
        o = result["metrics"]["overall"]
        print(
            f"   R@5={o['recall@5']:.3f} nDCG@5={o['ndcg@5']:.3f} MRR={o['mrr']:.3f} "
            f"index={result['timing']['index_total_s']:.1f}s "
            f"p50={result['timing']['query_p50_ms']:.1f}ms",
            flush=True,
        )
        (args.out / f"{config['name']}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    related = None
    if not args.no_related:
        best = best_config(results)
        related = {"config": best, **related_experiment(rankings[best], notes, manifest)}
        (args.out / "related_expansion.json").write_text(
            json.dumps(related, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    # O summary sempre reflete todos os JSONs gravados em --out.
    all_results = {}
    for n in all_configs():
        p = args.out / f"{n}.json"
        if p.exists():
            all_results[n] = json.loads(p.read_text(encoding="utf-8"))
    if related is None and (args.out / "related_expansion.json").exists():
        related = json.loads((args.out / "related_expansion.json").read_text(encoding="utf-8"))
    write_summary(all_results, related, args.out / "summary.md")
    print(f"resultados em {args.out.relative_to(ROOT) if args.out.is_absolute() else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
