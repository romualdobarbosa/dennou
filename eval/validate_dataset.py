"""Valida o dataset de eval de retrieval (vault sintético + queries rotuladas).

Uso: python3 eval/validate_dataset.py
Só stdlib. Sai com código 1 se encontrar algum problema.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VAULT = ROOT / "vault"
QUERIES = ROOT / "queries.jsonl"
MANIFEST = ROOT / "manifest.json"

EXPECTED_NOTES = 80
EXPECTED_QUERIES = 60
EXPECTED_KINDS = {"literal": 25, "paraphrase": 15, "cross_lingual": 10, "no_answer": 10}
REQUIRED_FIELDS = ["id", "title", "type", "tags", "area", "created", "source", "related"]
TYPES = {"syntax", "concept", "command", "error", "fact", "note"}
AREAS = {"programacao", "ciencia-da-computacao", "cotidiano", "filosofia", "misc"}
FILENAME_RE = re.compile(r"^(\d{14})-[a-z0-9-]+\.md$")
LONG_MIN_WORDS = 550
MIN_TAIL_QUERIES = 8

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def parse_list(value: str) -> list[str]:
    value = value.strip()
    if not (value.startswith("[") and value.endswith("]")):
        raise ValueError(f"lista inválida: {value!r}")
    inner = value[1:-1].strip()
    return [x.strip().strip('"') for x in inner.split(",")] if inner else []


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("arquivo não começa com '---'")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter sem fechamento")
    fm: dict = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"linha sem ':' no frontmatter: {line!r}")
        key, value = key.strip(), value.strip()
        if key in ("tags", "related"):
            fm[key] = parse_list(value)
        else:
            fm[key] = value.strip('"')
    return fm, text[end + 5 :]


def check_notes() -> dict[str, dict]:
    files = sorted(VAULT.glob("*.md"))
    if len(files) != EXPECTED_NOTES:
        err(f"esperado {EXPECTED_NOTES} notas, achei {len(files)}")
    notes: dict[str, dict] = {}
    for f in files:
        m = FILENAME_RE.match(f.name)
        if not m:
            err(f"{f.name}: nome fora do padrão YYYYMMDDHHMMSS-slug.md")
            continue
        try:
            fm, body = parse_frontmatter(f.read_text(encoding="utf-8"))
        except ValueError as e:
            err(f"{f.name}: {e}")
            continue
        missing = [k for k in REQUIRED_FIELDS if k not in fm]
        if missing:
            err(f"{f.name}: campos ausentes {missing}")
            continue
        nid = fm["id"]
        if nid != m.group(1):
            err(f"{f.name}: id {nid} não bate com o nome do arquivo")
        if nid in notes:
            err(f"{f.name}: id duplicado {nid}")
        if fm["type"] not in TYPES:
            err(f"{f.name}: type inválido {fm['type']!r}")
        if fm["area"] not in AREAS:
            err(f"{f.name}: area inválida {fm['area']!r}")
        if fm["source"] != "agent":
            err(f"{f.name}: source deveria ser 'agent'")
        if not re.fullmatch(r"\d{2}/\d{2}/\d{2}", fm["created"]):
            err(f"{f.name}: created fora do formato DD/MM/YY")
        if "## Links" not in body:
            err(f"{f.name}: corpo sem seção '## Links'")
        fm["_file"] = f.name
        fm["_words"] = len(body.split())
        fm["_body"] = body
        notes[nid] = fm

    for nid, fm in notes.items():
        for r in fm["related"]:
            if r not in notes:
                err(f"{fm['_file']}: related aponta para id inexistente {r}")
            elif r == nid:
                err(f"{fm['_file']}: related aponta para a própria nota")
            elif f"[[{notes[r]['_file'][:-3]}]]" not in fm["_body"]:
                err(f"{fm['_file']}: related {r} sem wiki-link correspondente em ## Links")
    return notes


def check_queries(notes: dict[str, dict]) -> list[dict]:
    lines = [ln for ln in QUERIES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) != EXPECTED_QUERIES:
        err(f"esperado {EXPECTED_QUERIES} queries, achei {len(lines)}")
    queries = []
    seen = set()
    for n, line in enumerate(lines, 1):
        try:
            q = json.loads(line)
        except json.JSONDecodeError as e:
            err(f"queries.jsonl linha {n}: JSON inválido ({e})")
            continue
        for k in ("id", "query", "kind", "relevant"):
            if k not in q:
                err(f"queries.jsonl linha {n}: campo {k!r} ausente")
        qid = q.get("id")
        if qid in seen:
            err(f"query id duplicado: {qid}")
        seen.add(qid)
        kind = q.get("kind")
        rel = q.get("relevant", {})
        if kind not in EXPECTED_KINDS:
            err(f"{qid}: kind inválido {kind!r}")
        if not str(q.get("query", "")).strip():
            err(f"{qid}: query vazia")
        for nid, grade in rel.items():
            if nid not in notes:
                err(f"{qid}: nota {nid} não existe")
            if grade not in (1, 2):
                err(f"{qid}: nota {nid} com grau {grade!r} (só 1 ou 2)")
        twos = sum(1 for g in rel.values() if g == 2)
        if kind == "no_answer" and rel:
            err(f"{qid}: no_answer precisa de relevant vazio")
        if kind != "no_answer" and twos == 0:
            err(f"{qid}: precisa de pelo menos uma nota com grau 2")
        if twos > 2:
            err(f"{qid}: mais de 2 notas com grau 2")
        queries.append(q)

    by_kind = Counter(q.get("kind") for q in queries)
    if dict(by_kind) != EXPECTED_KINDS:
        err(f"distribuição por kind {dict(by_kind)} != {EXPECTED_KINDS}")
    return queries


def check_manifest(notes: dict[str, dict], queries: list[dict]) -> None:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if man.get("notes") != len(notes):
        err(f"manifest.notes={man.get('notes')} mas há {len(notes)} notas")
    if man.get("queries") != len(queries):
        err(f"manifest.queries={man.get('queries')} mas há {len(queries)} queries")
    if man.get("by_kind") != dict(Counter(q["kind"] for q in queries)):
        err("manifest.by_kind não bate com queries.jsonl")
    long_notes = set(man.get("long_notes", []))
    for nid in long_notes:
        if nid not in notes:
            err(f"manifest.long_notes: id inexistente {nid}")
        elif notes[nid]["_words"] < LONG_MIN_WORDS:
            err(f"nota longa {nid} tem só {notes[nid]['_words']} palavras")
    qmap = {q["id"]: q for q in queries}
    tail = man.get("tail_answer_queries", [])
    if len(tail) < MIN_TAIL_QUERIES:
        err(f"só {len(tail)} tail_answer_queries (mínimo {MIN_TAIL_QUERIES})")
    for qid in tail:
        q = qmap.get(qid)
        if q is None:
            err(f"manifest.tail_answer_queries: query inexistente {qid}")
            continue
        if q["kind"] == "no_answer":
            err(f"{qid}: tail query não pode ser no_answer")
        answers = [nid for nid, g in q["relevant"].items() if g == 2]
        if not all(nid in long_notes for nid in answers):
            err(f"{qid}: tail query com resposta fora das notas longas")


def main() -> int:
    notes = check_notes()
    queries = check_queries(notes)
    check_manifest(notes, queries)
    if errors:
        print(f"FALHOU: {len(errors)} problema(s)")
        for e in errors:
            print(" -", e)
        return 1
    sizes = Counter(
        "longa" if n["_words"] >= LONG_MIN_WORDS else "média" if n["_words"] > 200 else "curta"
        for n in notes.values()
    )
    print(f"OK: {len(notes)} notas, {len(queries)} queries")
    print("  tipos:", dict(Counter(n["type"] for n in notes.values())))
    print("  tamanhos:", dict(sizes))
    print("  kinds:", dict(Counter(q["kind"] for q in queries)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
