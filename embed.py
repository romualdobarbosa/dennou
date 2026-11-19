"""
Pipeline de embedding para o vault de notas.
Insere ou atualiza uma nota no ChromaDB com base no seu frontmatter e body.
"""

import os
import re
import sys
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
MODEL_NAME = os.environ.get("DENNOU_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")

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


def open_collection(chroma_dir: str | Path, name: str = COLLECTION_NAME):
    """Abre (ou cria) uma coleção persistente do Chroma com distância cosseno."""
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def _get_collection():
    global _collection
    if _collection is None:
        _collection = open_collection(CHROMA_DIR)
    return _collection


def note_text(note: dict, include_title: bool = True) -> str:
    """Texto que vai pro embedding de uma nota: título + corpo (ou só o corpo)."""
    if include_title:
        return f"{note['title']}\n\n{note['body']}"
    return note["body"]


def distance_to_score(distance: float) -> float:
    """Converte a distância cosseno do Chroma no score mostrado na busca."""
    return round(1 - distance, 4)


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
    Insere ou atualiza uma nota no ChromaDB.
    Com sync_metadata, atualiza também as cores do graph.json e o TAGS.md
    (o sync_vault desliga e atualiza uma vez só no fim).
    Retorna o ID da nota embedada.
    """
    path = Path(path)
    note = parse_note(path)
    if note is None:
        raise ValueError(f"Nota inválida ou sem frontmatter: {path}")

    text_to_embed = note_text(note)

    model = _get_model()
    embedding = model.encode(text_to_embed).tolist()

    collection = _get_collection()
    collection.upsert(
        ids=[note["id"]],
        embeddings=[embedding],
        documents=[text_to_embed],
        metadatas=[
            {
                "title": note["title"],
                "type": note["type"],
                "tags": ", ".join(note["tags"]),
                "area": note["area"],
                "created": note["created"],
                "filename": note["filename"],
            }
        ],
    )

    if sync_metadata:
        sync_graph_colors()
        sync_tags()
    return note["id"]


def search(query: str, n_results: int = 5, filter_type: str = None) -> list[dict]:
    """
    Busca semântica no vault.
    Retorna lista de dicts com id, title, filename, score e trecho do body.
    """
    model = _get_model()
    query_embedding = model.encode(query).tolist()

    collection = _get_collection()
    where = {"type": filter_type} if filter_type else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append(
            {
                "id": results["ids"][0][i],
                "title": results["metadatas"][0][i]["title"],
                "filename": results["metadatas"][0][i]["filename"],
                "type": results["metadatas"][0][i]["type"],
                "score": distance_to_score(results["distances"][0][i]),
                "excerpt": results["documents"][0][i][:200],
            }
        )

    return output


def sync_vault():
    """Embeds todas as notas do vault (útil para reindexar tudo)."""
    notes = [p for p in VAULT_DIR.glob("*.md") if p.name != "Home.md"]
    if not notes:
        print("Nenhuma nota encontrada no vault.")
        return

    for path in notes:
        try:
            note_id = embed_note(path, sync_metadata=False)
            print(f"  embedado: {path.name} ({note_id})")
        except ValueError as e:
            print(f"  pulado: {e}")

    sync_graph_colors()
    sync_tags()
    print(f"\n{len(notes)} nota(s) processada(s).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python embed.py <comando> [args]")
        print("  sync                  — reindexar todo o vault")
        print("  tags                  — regenerar TAGS.md")
        print("  add <caminho>         — embedar uma nota específica")
        print("  search <query>        — busca semântica")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        sync_vault()

    elif cmd == "tags":
        sync_tags()
        print("TAGS.md atualizado.")

    elif cmd == "add" and len(sys.argv) == 3:
        note_id = embed_note(sys.argv[2])
        print(f"Nota embedada com id: {note_id}")

    elif cmd == "search" and len(sys.argv) >= 3:
        query = " ".join(sys.argv[2:])
        results = search(query)
        if not results:
            print("Nenhum resultado encontrado.")
        else:
            for r in results:
                print(f"[{r['score']}] {r['title']} ({r['type']}) — {r['filename']}")
                print(f"  {r['excerpt'][:120]}...")
                print()

    else:
        print(f"Comando desconhecido: {cmd}")
        sys.exit(1)
