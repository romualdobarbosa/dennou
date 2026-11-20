import json

from eval import run_agent_eval as a

SEARCH_OUTPUT = (
    "\rLoading weights: 100%\n"
    "[0.7236] Argumento padrão mutável (error) — 20260201000009-argumento-padrao\n"
    "  ## Solução ...\n\n"
    "[0.51] Git reflog (command) — 20260201000049-git-reflog  (abaixo do corte 0.55)\n"
    "  ## Uso ...\n"
)


def _event(role, block):
    return json.dumps({"type": role, "message": {"content": [block]}})


def test_parse_transcript_reads_search_hits_reads_and_result():
    lines = [
        _event(
            "assistant",
            {
                "type": "tool_use",
                "id": "t1",
                "name": "Bash",
                "input": {"command": '.venv/bin/python3 embed.py search "lista"'},
            },
        ),
        _event("user", {"type": "tool_result", "tool_use_id": "t1", "content": SEARCH_OUTPUT}),
        _event(
            "assistant",
            {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "/x/v/n.md"}},
        ),
        json.dumps({"type": "result", "result": "resposta", "num_turns": 3}),
    ]
    out = a.parse_transcript(lines)
    assert out["searches"][0]["hits"] == [
        {"score": 0.7236, "file": "20260201000009-argumento-padrao", "below": False},
        {"score": 0.51, "file": "20260201000049-git-reflog", "below": True},
    ]
    assert out["reads"] == ["/x/v/n.md"]
    assert out["answer"] == "resposta"
    assert out["is_error"] is False


def test_parse_transcript_without_result_is_error():
    assert a.parse_transcript([])["is_error"] is True


NOTES = {
    "20260201000049": {"title": "Git reflog", "filename": "20260201000049-git-reflog"},
    "20260201000009": {"title": "Argumento padrão mutável", "filename": "20260201000009-arg"},
}


def test_cited_notes_matches_title_without_accents():
    answer = "Fonte: nota *Argumento padrao mutavel*."
    assert a.cited_notes(answer, NOTES, set(NOTES)) == ["20260201000009"]


def test_cited_notes_ignores_notes_the_agent_never_saw():
    answer = "Rode git reflog pra achar o commit."
    assert a.cited_notes(answer, NOTES, set()) == []
    assert a.cited_notes(answer, NOTES, {"20260201000049"}) == ["20260201000049"]
