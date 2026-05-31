"""
Pipeline de embedding para o vault de notas.
Insere ou atualiza uma nota no ChromaDB com base no seu frontmatter e body.
"""

import re
import sys
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

VAULT_DIR = Path(__file__).parent / "vault"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
GRAPH_JSON = Path(__file__).parent / "vault" / ".obsidian" / "graph.json"
COLLECTION_NAME = "dennou"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Paleta de cores para novas tags (RGB decimal). Cores visualmente distintas.
_COLOR_PALETTE = [
    0xe74c3c, 0xf39c12, 0x1a73e8, 0xd35400, 0x27ae60,
    0x2980b9, 0x8e44ad, 0x16a085, 0xc0392b, 0xf1c40f,
    0x34495e, 0x7f8c8d, 0xa29bfe, 0xfd79a8, 0x00b894,
    0xe17055, 0x6c5ce7, 0xfdcb6e, 0x55efc4, 0xd63031,
]

_model = None
_client = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def _parse_note(path: Path) -> dict | None:
    """Extrai frontmatter e body de uma nota markdown."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return None

    raw_fm, body = match.group(1), match.group(2).strip()

    frontmatter = {}
    for line in raw_fm.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    note_id = frontmatter.get("id", "")
    if not note_id:
        return None

    return {
        "id": note_id,
        "title": frontmatter.get("title", "").strip('"'),
        "type": frontmatter.get("type", ""),
        "tags": frontmatter.get("tags", ""),
        "area": frontmatter.get("area", ""),
        "created": frontmatter.get("created", ""),
        "filename": path.stem,
        "body": body,
    }


def _extract_all_tags() -> set[str]:
    """Coleta todas as tags únicas de todas as notas do vault."""
    tags = set()
    for path in VAULT_DIR.glob("*.md"):
        if path.name == "Home.md":
            continue
        note = _parse_note(path)
        if note and note["tags"]:
            raw = note["tags"].strip("[]")
            for tag in raw.split(","):
                tag = tag.strip()
                if tag:
                    tags.add(tag)
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
        color = palette.pop(0) if palette else _COLOR_PALETTE[len(color_groups) % len(_COLOR_PALETTE)]
        color_groups.append({"query": f"tag:#{tag}", "color": {"a": 1, "rgb": color}})

    graph["colorGroups"] = color_groups
    GRAPH_JSON.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(new_tags)


TAGS_MD = Path(__file__).parent / "TAGS.md"


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


def embed_note(path: str | Path) -> str:
    """
    Insere ou atualiza uma nota no ChromaDB.
    Retorna o ID da nota embedada.
    """
    path = Path(path)
    note = _parse_note(path)
    if note is None:
        raise ValueError(f"Nota inválida ou sem frontmatter: {path}")

    text_to_embed = f"{note['title']}\n\n{note['body']}"

    model = _get_model()
    embedding = model.encode(text_to_embed).tolist()

    collection = _get_collection()
    collection.upsert(
        ids=[note["id"]],
        embeddings=[embedding],
        documents=[text_to_embed],
        metadatas=[{
            "title": note["title"],
            "type": note["type"],
            "tags": note["tags"],
            "area": note["area"],
            "created": note["created"],
            "filename": note["filename"],
        }],
    )

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
        output.append({
            "id": results["ids"][0][i],
            "title": results["metadatas"][0][i]["title"],
            "filename": results["metadatas"][0][i]["filename"],
            "type": results["metadatas"][0][i]["type"],
            "score": round(1 - results["distances"][0][i], 4),
            "excerpt": results["documents"][0][i][:200],
        })

    return output


def sync_vault():
    """Embeds todas as notas do vault (útil para reindexar tudo)."""
    notes = [p for p in VAULT_DIR.glob("*.md") if p.name != "Home.md"]
    if not notes:
        print("Nenhuma nota encontrada no vault.")
        return

    for path in notes:
        try:
            note_id = embed_note(path)
            print(f"  embedado: {path.name} ({note_id})")
        except ValueError as e:
            print(f"  pulado: {e}")

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
        print(f"TAGS.md atualizado.")

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
