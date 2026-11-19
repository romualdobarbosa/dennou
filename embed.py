"""
Pipeline de embedding para o vault de notas.
Insere ou atualiza uma nota no ChromaDB com base no seu frontmatter e body.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent

# Caminhos e modelo configuráveis por variável de ambiente (ex.: demo e eval
# usam um vault e um banco separados). Os defaults são os do uso normal.
VAULT_DIR = Path(os.environ.get("DENNOU_VAULT_DIR", ROOT / "vault"))
CHROMA_DIR = Path(os.environ.get("DENNOU_CHROMA_DIR", ROOT / "chroma_db"))
TAGS_MD = Path(os.environ.get("DENNOU_TAGS_FILE", ROOT / "TAGS.md"))
# Config do Obsidian do próprio vault; se não existir, as cores não são sincronizadas.
GRAPH_JSON = VAULT_DIR / ".obsidian" / "graph.json"
COLLECTION_NAME = "dennou"
# Formato do índice: um vetor por chunk de nota. Coleção sem essa marca é do
# formato antigo (um vetor por nota) e é recriada pelo `embed.py sync`.
INDEX_FORMAT = "chunks-v1"
# Chunks de até 256 tokens (ou o max_seq_length do modelo, se for menor: 128 no
# MiniLM), contando título e tokens especiais. É a config "minilm-chunk-title" do eval.
CHUNK_MAX_TOKENS = 256
CHUNK_WORD_OVERLAP = 0.2
# Score mínimo pra uma nota contar como relevante (o agente ignora as de baixo).
# 0.55 é o sugerido pelo eval pra config de produção: 10% de falso positivo
# nas perguntas sem resposta. Mudou o modelo ou o chunking, rode `make eval`.
DEFAULT_SCORE_THRESHOLD = 0.55
SCORE_THRESHOLD = float(os.environ.get("DENNOU_SCORE_THRESHOLD") or DEFAULT_SCORE_THRESHOLD)
MODEL_NAME = os.environ.get("DENNOU_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

# Log das buscas do CLI (JSONL, uma linha por busca). São consultas pessoais:
# logs/ fica no .gitignore. DENNOU_LOG_FILE troca o caminho; vazio ou "off" desliga.
DEFAULT_LOG_FILE = ROOT / "logs" / "search.jsonl"

# Paleta de cores para novas tags (RGB decimal). Cores visualmente distintas.
_COLOR_PALETTE = [
    0xE74C3C,
    0xF39C12,
    0x1A73E8,
    0xD35400,
    0x27AE60,
    0x2980B9,
    0x8E44AD,
    0x16A085,
    0xC0392B,
    0xF1C40F,
    0x34495E,
    0x7F8C8D,
    0xA29BFE,
    0xFD79A8,
    0x00B894,
    0xE17055,
    0x6C5CE7,
    0xFDCB6E,
    0x55EFC4,
    0xD63031,
]

_model = None
_collection = None


def load_model(name: str = MODEL_NAME, device: str | None = None) -> SentenceTransformer:
    """
    Carrega um modelo do sentence-transformers.
    Tenta só o cache local primeiro: evita a checagem de versão no
    Hugging Face Hub a cada execução. Sem cache (primeira vez, ou
    modelo trocado), cai no carregamento normal, que baixa o modelo.
    """
    try:
        return SentenceTransformer(name, device=device, local_files_only=True)
    except OSError:
        return SentenceTransformer(name, device=device)


def _get_model():
    global _model
    if _model is None:
        _model = load_model()
    return _model


def _client(chroma_dir: str | Path):
    return chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )


def _collection_metadata() -> dict:
    return {"hnsw:space": "cosine", "dennou_index": INDEX_FORMAT}


def is_current_format(collection) -> bool:
    """A coleção foi criada no formato atual (chunks)? Senão, precisa de `sync`."""
    return (collection.metadata or {}).get("dennou_index") == INDEX_FORMAT


def open_collection(chroma_dir: str | Path, name: str = COLLECTION_NAME):
    """Abre (ou cria) uma coleção persistente do Chroma com distância cosseno."""
    client = _client(chroma_dir)
    collection = client.get_or_create_collection(name=name, metadata=_collection_metadata())
    if not is_current_format(collection) and collection.count() == 0:
        # Coleção vazia criada por uma versão antiga: recria já com a marca do formato.
        client.delete_collection(name)
        collection = client.create_collection(name=name, metadata=_collection_metadata())
    return collection


def _get_collection():
    global _collection
    if _collection is None:
        _collection = open_collection(CHROMA_DIR)
    return _collection


def note_text(note: dict, include_title: bool = True) -> str:
    """Texto da nota inteira: título + corpo (ou só o corpo)."""
    if include_title:
        return f"{note['title']}\n\n{note['body']}"
    return note["body"]


def distance_to_score(distance: float) -> float:
    """Converte a distância cosseno do Chroma no score mostrado na busca."""
    return round(1 - distance, 4)


# --------------------------------------------------------------------------- chunking


def count_tokens(model: SentenceTransformer, text: str) -> int:
    """Tokens que o modelo veria, com os especiais e sem truncar."""
    encoded = model.tokenizer(text, add_special_tokens=True, truncation=False, verbose=False)
    return len(encoded["input_ids"])


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
    Parágrafo que sozinho não cabe vira janelas de palavras com sobreposição
    de CHUNK_WORD_OVERLAP.
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
            start = max(start + 1, end - int((end - start) * CHUNK_WORD_OVERLAP))
    if current:
        chunks.append(current)
    return chunks


def note_chunks(
    note: dict,
    model: SentenceTransformer,
    include_title: bool = True,
    passage_prefix: str = "",
    max_tokens: int = CHUNK_MAX_TOKENS,
) -> list[str]:
    """
    Textos que vão pro embedding de uma nota: o corpo em chunks de até
    min(max_tokens, max_seq_length do modelo) tokens, cada um com o prefixo e
    o título na frente (contados no limite, então nenhum chunk é truncado).
    É a mesma função que o eval usa.
    """
    head = passage_prefix + (f"{note['title']}\n\n" if include_title else "")
    limit = min(max_tokens, model.max_seq_length)
    chunks = chunk_body(note["body"], lambda text: count_tokens(model, head + text) <= limit)
    if not chunks:  # corpo vazio: indexa só o título
        return [(passage_prefix + note_text(note, include_title)).strip()]
    return [head + chunk for chunk in chunks]


def index_note(collection, model: SentenceTransformer, note: dict, texts=None) -> int:
    """
    Grava os chunks de uma nota (ids "<note_id>#<n>", metadado note_id) e apaga
    os que ela tinha antes, inclusive o vetor único do formato antigo. Assim
    reindexar não duplica e nota que encolheu não deixa chunk órfão.
    Retorna quantos chunks foram gravados.
    """
    if texts is None:
        texts = note_chunks(note, model)
    embeddings = model.encode(texts)  # antes de apagar: se falhar, o índice fica como estava

    collection.delete(where={"note_id": note["id"]})
    collection.delete(ids=[note["id"]])

    base = {
        "note_id": note["id"],
        "title": note["title"],
        "type": note["type"],
        "area": note["area"],
        "created": note["created"],
        "filename": note["filename"],
    }
    if note["tags"]:  # o Chroma não aceita lista vazia como metadado
        base["tags"] = note["tags"]
    collection.add(
        ids=[f"{note['id']}#{i}" for i in range(len(texts))],
        embeddings=[e.tolist() for e in embeddings],
        documents=texts,
        metadatas=[{**base, "chunk": i} for i in range(len(texts))],
    )
    return len(texts)


def best_chunk_per_note(results: dict) -> list[dict]:
    """
    Junta o resultado de um `collection.query` por nota: score da nota = maior
    score entre os chunks dela; cada nota aparece uma vez, em ordem de score.
    Entrada sem note_id (formato antigo) conta como nota pelo próprio id.
    """
    ids, metas, dists = results["ids"][0], results["metadatas"][0], results["distances"][0]
    docs = (results.get("documents") or [None])[0] or [None] * len(ids)
    best: dict[str, dict] = {}
    for chunk_id, meta, dist, doc in zip(ids, metas, dists, docs, strict=True):
        meta = meta or {}
        note_id = meta.get("note_id") or chunk_id
        score = distance_to_score(dist)
        if note_id not in best or score > best[note_id]["score"]:
            best[note_id] = {"note_id": note_id, "score": score, "metadata": meta, "document": doc}
    return sorted(best.values(), key=lambda h: (-h["score"], h["note_id"]))


def _unquote(value: str) -> str:
    """Tira aspas YAML simples ou duplas em volta do valor, se houver."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace("''", "'") if value[0] == "'" else inner.replace('\\"', '"')
    return value


def _parse_value(value: str) -> str | list[str]:
    """Valor de uma linha `chave: valor`: lista inline `[a, b]` ou escalar."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_unquote(v.strip()) for v in value[1:-1].split(",") if v.strip()]
    return _unquote(value)


def parse_frontmatter(raw: str) -> dict[str, str | list[str]]:
    """
    Parser do subconjunto de YAML que as notas usam: `chave: valor` (o valor
    pode ter ":"), lista inline `[a, b]` e lista em bloco (`chave:` seguida de
    linhas `- item`). Feito à mão de propósito: um YAML estrito recusaria
    título sem aspas com ": ", que o Obsidian aceita.
    """
    frontmatter: dict[str, str | list[str]] = {}
    key = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if key and (stripped.startswith("- ") or stripped == "-"):
            item = _unquote(stripped[1:].strip())
            current = frontmatter.get(key)
            frontmatter[key] = [*current, item] if isinstance(current, list) else [item]
            continue
        if ":" in line and not line[0].isspace():
            k, _, value = line.partition(":")
            key = k.strip()
            frontmatter[key] = _parse_value(value)
    return frontmatter


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [v for v in value if v]
    return [value] if value else []


def parse_note(path: Path) -> dict | None:
    """Extrai frontmatter e body de uma nota markdown. Sem frontmatter ou sem id: None."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---[ \t]*(?:\n(.*))?\Z", text, re.DOTALL)
    if not match:
        return None

    frontmatter = parse_frontmatter(match.group(1))
    body = (match.group(2) or "").strip()

    note_id = frontmatter.get("id", "")
    if not note_id or not isinstance(note_id, str):
        return None

    def scalar(key: str) -> str:
        value = frontmatter.get(key, "")
        return value if isinstance(value, str) else ", ".join(value)

    return {
        "id": note_id,
        "title": scalar("title"),
        "type": scalar("type"),
        "tags": _as_list(frontmatter.get("tags")),
        "area": scalar("area"),
        "created": scalar("created"),
        "related": _as_list(frontmatter.get("related")),
        "filename": path.stem,
        "body": body,
    }


def _extract_all_tags() -> set[str]:
    """Coleta todas as tags únicas de todas as notas do vault."""
    tags = set()
    for path in VAULT_DIR.glob("*.md"):
        if path.name == "Home.md":
            continue
        note = parse_note(path)
        if note:
            tags.update(note["tags"])
    return tags


def sync_graph_colors() -> int:
    """
    Lê as tags do vault e adiciona ao graph.json uma cor para cada tag nova.
    Retorna o número de novas tags adicionadas.
    """
    import json

    if not GRAPH_JSON.exists():
        return 0

    graph = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    color_groups = graph.get("colorGroups", [])

    existing_tags = {
        g["query"][5:]  # strip "tag:#"
        for g in color_groups
        if g.get("query", "").startswith("tag:#")
    }

    new_tags = sorted(_extract_all_tags() - existing_tags)
    if not new_tags:
        return 0

    used_colors = {g["color"]["rgb"] for g in color_groups if "color" in g}
    palette = [c for c in _COLOR_PALETTE if c not in used_colors] or list(_COLOR_PALETTE)

    for tag in new_tags:
        color = (
            palette.pop(0) if palette else _COLOR_PALETTE[len(color_groups) % len(_COLOR_PALETTE)]
        )
        color_groups.append({"query": f"tag:#{tag}", "color": {"a": 1, "rgb": color}})

    graph["colorGroups"] = color_groups
    GRAPH_JSON.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(new_tags)


def sync_tags() -> None:
    """Regenera TAGS.md com todas as tags únicas do vault, em ordem alfabética."""
    tags = sorted(_extract_all_tags())
    lines = [
        "# Tags disponíveis\n",
        "Use as tags existentes ao criar uma nota.",
        "Se precisar de uma tag nova, crie — ela será adicionada aqui automaticamente.\n",
    ]
    for tag in tags:
        lines.append(f"- {tag}")
    TAGS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def embed_note(path: str | Path, sync_metadata: bool = True) -> str:
    """
    Insere ou atualiza uma nota no ChromaDB (todos os chunks dela).
    Com sync_metadata, atualiza também as cores do graph.json e o TAGS.md
    (o sync_vault desliga e atualiza uma vez só no fim).
    Retorna o ID da nota embedada.
    """
    path = Path(path)
    note = parse_note(path)
    if note is None:
        raise ValueError(f"Nota inválida ou sem frontmatter: {path}")

    index_note(_get_collection(), _get_model(), note)

    if sync_metadata:
        sync_graph_colors()
        sync_tags()
    return note["id"]


def _excerpt(document: str | None, title: str, size: int = 300) -> str:
    """Trecho do chunk que casou, sem o título que vai na frente de todo chunk."""
    text = document or ""
    if title and text.startswith(f"{title}\n\n"):
        text = text[len(title) + 2 :]
    return text[:size]


def _where(filter_type: str | None, filter_tag: str | None) -> dict | None:
    """Filtro do Chroma. tags é metadado de lista, filtrado com $contains."""
    conditions = []
    if filter_type:
        conditions.append({"type": filter_type})
    if filter_tag:
        conditions.append({"tags": {"$contains": filter_tag}})
    if len(conditions) > 1:
        return {"$and": conditions}
    return conditions[0] if conditions else None


def search(
    query: str,
    n_results: int = 5,
    filter_type: str | None = None,
    filter_tag: str | None = None,
) -> list[dict]:
    """
    Busca semântica no vault. Uma entrada por nota (o chunk de maior score),
    em ordem de score: dicts com id, title, filename, type, score, excerpt
    (trecho do chunk que casou) e relevant (score >= SCORE_THRESHOLD).
    """
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []

    query_embedding = _get_model().encode(query).tolist()
    where = _where(filter_type, filter_tag)

    # Vários chunks podem ser da mesma nota: pede mais itens que notas e
    # dobra enquanto faltar nota distinta e ainda houver item no índice.
    fetch = min(total, max(n_results * 10, 50))
    while True:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = best_chunk_per_note(results)
        returned = len(results["ids"][0])
        if len(hits) >= n_results or returned < fetch or fetch >= total:
            break
        fetch = min(total, fetch * 2)

    output = []
    for hit in hits[:n_results]:
        meta = hit["metadata"]
        output.append(
            {
                "id": hit["note_id"],
                "title": meta.get("title", ""),
                "filename": meta.get("filename", ""),
                "type": meta.get("type", ""),
                "score": hit["score"],
                "excerpt": _excerpt(hit["document"], meta.get("title", "")),
                "relevant": hit["score"] >= SCORE_THRESHOLD,
            }
        )
    return output


def sync_vault():
    """
    Reindexa o vault inteiro do zero: monta uma coleção nova e só no fim troca
    pela atual. Assim não sobra vetor de nota apagada nem do formato antigo.
    """
    global _collection
    notes = sorted(p for p in VAULT_DIR.glob("*.md") if p.name != "Home.md")
    if not notes:
        print("Nenhuma nota encontrada no vault.")
        return

    client = _client(CHROMA_DIR)
    existing = {c.name for c in client.list_collections()}
    staging = f"{COLLECTION_NAME}-rebuild"
    if staging in existing:  # sobra de um sync interrompido
        client.delete_collection(staging)
    collection = client.create_collection(name=staging, metadata=_collection_metadata())

    model = _get_model()
    for path in notes:
        note = parse_note(path)
        if note is None:
            print(f"  pulado: Nota inválida ou sem frontmatter: {path}")
            continue
        n_chunks = index_note(collection, model, note)
        print(f"  embedado: {path.name} ({note['id']}, {n_chunks} chunk(s))")

    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
    collection.modify(name=COLLECTION_NAME)
    _collection = collection

    sync_graph_colors()
    sync_tags()
    print(f"\n{len(notes)} nota(s) processada(s).")


def log_file() -> Path | None:
    """Arquivo do log de buscas, ou None se desligado (DENNOU_LOG_FILE vazio/off)."""
    raw = os.environ.get("DENNOU_LOG_FILE")
    if raw is None:
        return DEFAULT_LOG_FILE
    if raw.strip().lower() in ("", "0", "off", "false", "no"):
        return None
    return Path(raw)


def log_search(
    query: str,
    results: list[dict],
    latency_ms: float,
    k: int,
    filter_type: str | None = None,
    filter_tag: str | None = None,
) -> None:
    """Anexa uma linha JSONL com a busca. Falha no log não derruba a busca."""
    path = log_file()
    if path is None:
        return
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "query": query,
        "k": k,
        "type": filter_type,
        "tag": filter_tag,
        "results": [{"note_id": r["id"], "score": r["score"]} for r in results],
        "above_threshold": sum(r["relevant"] for r in results),
        "threshold": SCORE_THRESHOLD,
        "latency_ms": round(latency_ms, 1),
        "model": MODEL_NAME,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"aviso: não deu pra gravar o log de busca em {path}: {e}", file=sys.stderr)


def _warn_if_old_format() -> None:
    collection = _get_collection()
    if not is_current_format(collection):
        print(
            "aviso: o índice está no formato antigo (um vetor por nota). "
            "Rode `embed.py sync` pra reindexar em chunks.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="embed.py", description="Índice e busca do vault.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="reindexar todo o vault do zero")
    sub.add_parser("tags", help="regenerar TAGS.md")
    p_add = sub.add_parser("add", help="embedar uma nota específica")
    p_add.add_argument("path")
    p_search = sub.add_parser("search", help="busca semântica")
    p_search.add_argument("query", nargs="+")
    p_search.add_argument("--type", dest="filter_type", help="só notas desse type")
    p_search.add_argument("--tag", dest="filter_tag", help="só notas com essa tag")
    p_search.add_argument("-k", type=int, default=5, help="quantas notas (default 5)")
    args = parser.parse_args(argv)

    if args.cmd == "sync":
        sync_vault()
    elif args.cmd == "tags":
        sync_tags()
        print("TAGS.md atualizado.")
    elif args.cmd == "add":
        _warn_if_old_format()
        note_id = embed_note(args.path)
        print(f"Nota embedada com id: {note_id}")
    elif args.cmd == "search":
        _warn_if_old_format()
        query = " ".join(args.query)
        _get_model()  # carregar o modelo fica fora da latência medida
        t0 = time.perf_counter()
        results = search(
            query, n_results=args.k, filter_type=args.filter_type, filter_tag=args.filter_tag
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        log_search(query, results, latency_ms, args.k, args.filter_type, args.filter_tag)
        if not results:
            print("Nenhum resultado encontrado.")
        for r in results:
            below = "" if r["relevant"] else f"  (abaixo do corte {SCORE_THRESHOLD})"
            print(f"[{r['score']}] {r['title']} ({r['type']}) — {r['filename']}{below}")
            print(f"  {' '.join(r['excerpt'].split())[:200]}...")
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
