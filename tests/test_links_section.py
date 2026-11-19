"""A seção `## Links` (wiki-links do Obsidian) fica fora do texto embedado."""

import embed

BODY = """## O que faz
Cria uma branch nova.

```bash
git branch nova
## Links  (dentro de bloco de código não conta)
```

## Links
[[20260101000003-git-commit]]
[[20260101000005-git-merge]]"""


def test_strip_links_section_drops_heading_and_wikilinks():
    out = embed.strip_links_section(BODY)
    assert "[[" not in out
    assert "\n## Links\n" not in out
    assert out.startswith("## O que faz")
    assert "## Links  (dentro de bloco de código não conta)" in out


def test_strip_links_section_keeps_sections_after_it():
    body = "## Links\n[[a]]\n\n## Gotchas\nCuidado com X."
    assert embed.strip_links_section(body) == "## Gotchas\nCuidado com X."


def test_strip_links_section_without_links_is_noop():
    assert embed.strip_links_section("## Definição\nTexto.") == "## Definição\nTexto."


def test_note_text_respects_keep_links():
    note = {"title": "Branch", "body": BODY}
    assert "[[" not in embed.note_text(note)
    assert "[[" in embed.note_text(note, keep_links=True)


def test_note_chunks_never_embed_wikilinks(isolated_embed):
    model = embed._get_model()
    note = {"title": "Branch", "body": BODY}
    assert not any("[[" in c for c in embed.note_chunks(note, model))
    assert any("[[" in c for c in embed.note_chunks(note, model, keep_links=True))
