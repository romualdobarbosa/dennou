import pytest

import embed


@pytest.fixture(autouse=True)
def isolated_embed(tmp_path, monkeypatch):
    """
    Todo teste roda com vault, Chroma, TAGS.md e log em tmp_path: nenhum teste
    encosta no vault real, no chroma_db/ ou no TAGS.md do repo.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(embed, "VAULT_DIR", vault)
    monkeypatch.setattr(embed, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(embed, "TAGS_MD", tmp_path / "TAGS.md")
    monkeypatch.setattr(embed, "GRAPH_JSON", vault / ".obsidian" / "graph.json")
    monkeypatch.setattr(embed, "_collection", None)
    monkeypatch.setenv("DENNOU_LOG_FILE", "off")
    return vault
