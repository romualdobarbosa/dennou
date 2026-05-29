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
COLLECTION_NAME = "dennou"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

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


def embed_note(path: str | Path) -> str:
    """
    Insere ou atualiza uma nota no ChromaDB.
    Retorna o ID da nota embedada.
    """
    path = Path(path)
    note = _parse_note(path)
    if note is None:
        raise ValueError(f"Nota inválida ou sem frontmatter: {path}")

    # Texto que será embedado: título + body (mais rico semanticamente)
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

    print(f"\n{len(notes)} nota(s) processada(s).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python embed.py <comando> [args]")
        print("  sync                  — reindexar todo o vault")
        print("  add <caminho>         — embedar uma nota específica")
        print("  search <query>        — busca semântica")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        sync_vault()

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
