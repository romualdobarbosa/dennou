"""Parser de frontmatter do embed.py (sem modelo, sem Chroma)."""

import embed


def write(tmp_path, text, name="20260101000001-nota.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_inline_frontmatter(tmp_path):
    path = write(
        tmp_path,
        '---\nid: 20260101000001\ntitle: "Listas"\ntype: syntax\n'
        "tags: [python, lista]\narea: programacao\ncreated: 01/01/26\n"
        "related: [20260101000002]\n---\n\n## O que é\nCorpo.\n",
    )
    note = embed.parse_note(path)
    assert note["id"] == "20260101000001"
    assert note["title"] == "Listas"
    assert note["type"] == "syntax"
    assert note["tags"] == ["python", "lista"]
    assert note["related"] == ["20260101000002"]
    assert note["created"] == "01/01/26"
    assert note["filename"] == "20260101000001-nota"
    assert note["body"] == "## O que é\nCorpo."


def test_title_with_colon(tmp_path):
    quoted = write(tmp_path, '---\nid: 1\ntitle: "Git: rebase vs merge"\n---\ncorpo\n', "a.md")
    bare = write(tmp_path, "---\nid: 2\ntitle: SQL: JOIN e WHERE\n---\ncorpo\n", "b.md")
    assert embed.parse_note(quoted)["title"] == "Git: rebase vs merge"
    assert embed.parse_note(bare)["title"] == "SQL: JOIN e WHERE"


def test_single_quoted_title(tmp_path):
    path = write(tmp_path, "---\nid: 1\ntitle: 'It''s: ok'\n---\ncorpo\n")
    assert embed.parse_note(path)["title"] == "It's: ok"


def test_block_lists(tmp_path):
    path = write(
        tmp_path,
        "---\nid: 1\ntitle: x\ntags:\n  - git\n  - rebase\nrelated:\n  - 2\n  - 3\n"
        "type: concept\n---\ncorpo\n",
    )
    note = embed.parse_note(path)
    assert note["tags"] == ["git", "rebase"]
    assert note["related"] == ["2", "3"]
    assert note["type"] == "concept"


def test_empty_lists(tmp_path):
    path = write(tmp_path, "---\nid: 1\ntitle: x\ntags: []\nrelated:\n---\ncorpo\n")
    note = embed.parse_note(path)
    assert note["tags"] == []
    assert note["related"] == []


def test_crlf_and_empty_body(tmp_path):
    path = write(tmp_path, "---\r\nid: 1\r\ntitle: x\r\ntags: [a]\r\n---")
    note = embed.parse_note(path)
    assert note["tags"] == ["a"]
    assert note["body"] == ""


def test_note_without_id_or_frontmatter_is_skipped(tmp_path):
    assert embed.parse_note(write(tmp_path, "---\ntitle: x\n---\ncorpo\n", "a.md")) is None
    assert embed.parse_note(write(tmp_path, "só texto\n", "b.md")) is None
