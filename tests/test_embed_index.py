"""
Índice e busca do embed.py com Chroma em tmp_path e o modelo real (em cache).
Mais lentos que os outros testes: carregam o MiniLM uma vez por sessão.
"""

import json

import pytest

import embed

PARAGRAPHS = [
    "O git rebase reaplica os commits do branch atual em cima de outro branch, "
    "deixando o histórico linear sem commits de merge.",
    "O rebase interativo permite reordenar, juntar e editar commits antes de publicar.",
    "Depois de um rebase em branch já publicado, é preciso fazer push forçado com lease.",
    "O PostgreSQL usa MVCC para isolar transações sem travar leituras.",
    "No Linux, o comando chmod muda as permissões de leitura, escrita e execução.",
    "Uma lista em Python é mutável e aceita elementos de tipos diferentes.",
    "O systemd gerencia serviços e o journalctl mostra os logs deles.",
    "Expressões regulares descrevem padrões de texto com classes e quantificadores.",
]


def write_note(vault, note_id, title, body, type_="concept", tags=("git",)):
    tags_yaml = ", ".join(tags)
    path = vault / f"{note_id}-nota.md"
    path.write_text(
        f'---\nid: {note_id}\ntitle: "{title}"\ntype: {type_}\ntags: [{tags_yaml}]\n'
        f"area: programacao\ncreated: 01/01/26\nsource: agent\nrelated: []\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return path


def long_body(repeat=3):
    return "\n\n".join(p for _ in range(repeat) for p in PARAGRAPHS)


def chunk_ids(note_id):
    got = embed._get_collection().get(where={"note_id": note_id})["ids"]
    return sorted(got, key=lambda i: int(i.split("#")[1]))


def test_long_note_becomes_several_chunks(isolated_embed):
    path = write_note(isolated_embed, "1", "Rebase", long_body())
    embed.embed_note(path)
    ids = chunk_ids("1")
    assert len(ids) > 1
    assert ids == [f"1#{i}" for i in range(len(ids))]
    docs = embed._get_collection().get(ids=ids)["documents"]
    assert all(d.startswith("Rebase\n\n") for d in docs)
    model = embed._get_model()
    assert all(embed.count_tokens(model, d) <= model.max_seq_length for d in docs)


def test_reindex_does_not_duplicate(isolated_embed):
    path = write_note(isolated_embed, "1", "Rebase", long_body())
    embed.embed_note(path)
    first = embed._get_collection().count()
    embed.embed_note(path)
    assert embed._get_collection().count() == first


def test_shrinking_note_leaves_no_orphan_chunk(isolated_embed):
    path = write_note(isolated_embed, "1", "Rebase", long_body())
    embed.embed_note(path)
    assert len(chunk_ids("1")) > 1
    write_note(isolated_embed, "1", "Rebase", PARAGRAPHS[0])
    embed.embed_note(path)
    assert chunk_ids("1") == ["1#0"]
    assert embed._get_collection().count() == 1


def test_add_removes_legacy_single_vector(isolated_embed):
    path = write_note(isolated_embed, "1", "Rebase", PARAGRAPHS[0])
    collection = embed._get_collection()
    dim = embed._get_model().get_embedding_dimension()
    collection.add(ids=["1"], embeddings=[[0.1] * dim], metadatas=[{"title": "velha"}])
    embed.embed_note(path)
    assert collection.get()["ids"] == ["1#0"]


def test_empty_body_indexes_title(isolated_embed):
    path = write_note(isolated_embed, "1", "Só o título", "")
    embed.embed_note(path)
    assert embed._get_collection().get()["documents"] == ["Só o título"]


@pytest.fixture
def three_notes(isolated_embed):
    write_note(isolated_embed, "1", "git rebase", PARAGRAPHS[0], "command", ("git", "historico"))
    write_note(isolated_embed, "2", "MVCC no PostgreSQL", PARAGRAPHS[3], "concept", ("sql",))
    write_note(isolated_embed, "3", "Rebase interativo", PARAGRAPHS[1], "concept", ("git",))
    for path in sorted(isolated_embed.glob("*.md")):
        embed.embed_note(path, sync_metadata=False)


def test_search_filters_by_type(three_notes):
    results = embed.search("rebase de commits", filter_type="concept")
    assert {r["id"] for r in results} == {"2", "3"}
    assert all(r["type"] == "concept" for r in results)


def test_search_filters_by_tag(three_notes):
    assert {r["id"] for r in embed.search("rebase", filter_tag="git")} == {"1", "3"}
    assert [r["id"] for r in embed.search("rebase", filter_tag="sql")] == ["2"]
    both = embed.search("rebase", filter_type="concept", filter_tag="git")
    assert [r["id"] for r in both] == ["3"]
    assert embed.search("rebase", filter_tag="inexistente") == []


def test_search_result_shape_and_threshold_flag(three_notes):
    results = embed.search("como fazer rebase no git")
    assert results[0]["id"] in {"1", "3"}
    assert set(results[0]) >= {"id", "title", "filename", "type", "score", "excerpt"}
    for r in results:
        assert r["relevant"] == (r["score"] >= embed.SCORE_THRESHOLD)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_search_dedupes_notes_and_excerpt_is_matched_chunk(isolated_embed):
    write_note(isolated_embed, "1", "Miscelânea", long_body(4))
    write_note(isolated_embed, "2", "Listas", PARAGRAPHS[5], "syntax", ("python",))
    write_note(isolated_embed, "3", "Permissões", PARAGRAPHS[4], "command", ("linux",))
    for path in sorted(isolated_embed.glob("*.md")):
        embed.embed_note(path, sync_metadata=False)
    assert len(chunk_ids("1")) > 3

    results = embed.search("journalctl mostra os logs do systemd", n_results=3)
    ids = [r["id"] for r in results]
    assert len(ids) == len(set(ids)) == 3
    top = results[0]
    assert top["id"] == "1"
    assert "journalctl" in top["excerpt"]
    assert not top["excerpt"].startswith("Miscelânea")


def test_best_chunk_per_note_takes_max_and_handles_legacy():
    results = {
        "ids": [["a#0", "b#0", "a#1", "legacy"]],
        "metadatas": [[{"note_id": "a"}, {"note_id": "b"}, {"note_id": "a"}, {}]],
        "distances": [[0.5, 0.3, 0.1, 0.2]],
        "documents": [["a0", "b0", "a1", "old"]],
    }
    hits = embed.best_chunk_per_note(results)
    assert [(h["note_id"], h["score"], h["document"]) for h in hits] == [
        ("a", 0.9, "a1"),
        ("legacy", 0.8, "old"),
        ("b", 0.7, "b0"),
    ]


def test_sync_migrates_legacy_index_and_drops_deleted_notes(isolated_embed):
    write_note(isolated_embed, "1", "Rebase", long_body())
    write_note(isolated_embed, "2", "MVCC", PARAGRAPHS[3], tags=("sql",))
    (isolated_embed / "sem-id.md").write_text("---\ntitle: x\n---\ncorpo\n", encoding="utf-8")

    # Banco no formato antigo: coleção sem marca, um vetor por nota, e uma
    # nota que já foi apagada do vault.
    client = embed._client(embed.CHROMA_DIR)
    legacy = client.create_collection(embed.COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
    dim = embed._get_model().get_embedding_dimension()
    legacy.add(
        ids=["1", "2", "99"],
        embeddings=[[0.1] * dim] * 3,
        metadatas=[{"title": "x", "tags": "[git]"}] * 3,
    )
    assert not embed.is_current_format(embed._get_collection())

    embed.sync_vault()

    collection = embed._get_collection()
    assert embed.is_current_format(collection)
    ids = collection.get()["ids"]
    assert all("#" in i for i in ids)
    assert {i.split("#")[0] for i in ids} == {"1", "2"}
    names = {c.name for c in embed._client(embed.CHROMA_DIR).list_collections()}
    assert names == {embed.COLLECTION_NAME}
    # Reabrindo do disco (outro processo) continua no formato novo.
    assert embed.is_current_format(embed.open_collection(embed.CHROMA_DIR))
    assert [r["id"] for r in embed.search("MVCC", filter_tag="sql")] == ["2"]


def test_sync_updates_graph_and_tags_once(isolated_embed, monkeypatch):
    for i in range(3):
        write_note(isolated_embed, str(i), f"Nota {i}", PARAGRAPHS[i])
    calls = {"graph": 0, "tags": 0}
    real_graph, real_tags = embed.sync_graph_colors, embed.sync_tags

    def graph():
        calls["graph"] += 1
        return real_graph()

    def tags():
        calls["tags"] += 1
        real_tags()

    monkeypatch.setattr(embed, "sync_graph_colors", graph)
    monkeypatch.setattr(embed, "sync_tags", tags)
    embed.sync_vault()
    assert calls == {"graph": 1, "tags": 1}


def test_sync_writes_tags_md_and_graph_colors(isolated_embed):
    obsidian = isolated_embed / ".obsidian"
    obsidian.mkdir()
    embed.GRAPH_JSON.write_text(json.dumps({"colorGroups": []}), encoding="utf-8")
    write_note(isolated_embed, "1", "Rebase", PARAGRAPHS[0], tags=("git", "historico"))
    (isolated_embed / "2-bloco.md").write_text(
        "---\nid: 2\ntitle: x\ntags:\n  - sql\n---\ncorpo\n", encoding="utf-8"
    )
    embed.sync_vault()

    tags_md = embed.TAGS_MD.read_text(encoding="utf-8")
    for tag in ("git", "historico", "sql"):
        assert f"- {tag}\n" in tags_md
    groups = json.loads(embed.GRAPH_JSON.read_text(encoding="utf-8"))["colorGroups"]
    assert {g["query"] for g in groups} == {"tag:#git", "tag:#historico", "tag:#sql"}


def test_cli_search_logs_jsonl(three_notes, tmp_path, monkeypatch, capsys):
    log = tmp_path / "logs" / "search.jsonl"
    monkeypatch.setenv("DENNOU_LOG_FILE", str(log))
    assert embed.main(["search", "rebase", "de", "commits", "--tag", "git", "-k", "2"]) == 0
    assert "git rebase" in capsys.readouterr().out
    (line,) = log.read_text(encoding="utf-8").splitlines()
    record = json.loads(line)
    assert record["query"] == "rebase de commits"
    assert record["tag"] == "git" and record["k"] == 2
    assert [r["note_id"] for r in record["results"]] == [
        r["id"] for r in embed.search("rebase de commits", n_results=2, filter_tag="git")
    ]
    assert record["model"] == embed.MODEL_NAME
    assert record["threshold"] == embed.SCORE_THRESHOLD
    assert 0 <= record["above_threshold"] <= 2
    assert record["latency_ms"] > 0


def test_cli_search_log_can_be_disabled(three_notes, tmp_path, monkeypatch):
    monkeypatch.setenv("DENNOU_LOG_FILE", "off")
    embed.main(["search", "rebase"])
    assert embed.log_file() is None
    assert not list(tmp_path.rglob("*.jsonl"))


def test_cli_marks_results_below_cut(three_notes, monkeypatch, capsys):
    monkeypatch.setattr(embed, "SCORE_THRESHOLD", 0.99)
    embed.main(["search", "rebase"])
    out = capsys.readouterr().out
    assert out.count("(abaixo do corte 0.99)") == 3
