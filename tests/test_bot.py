"""bot.py com Telegram e `claude -p` mockados: nada sai pra rede nem roda o agente."""

import json
import re
import subprocess
from pathlib import Path

import pytest

import bot

OWNER = "111"


@pytest.fixture
def tg_calls(tmp_path, monkeypatch):
    """Telegram falso, sessão em tmp_path e dono fixo. Devolve as chamadas feitas."""
    calls = []
    monkeypatch.setattr(bot, "tg", lambda method, **params: calls.append((method, params)))
    monkeypatch.setattr(bot, "SESSION_FILE", tmp_path / ".bot_session")
    monkeypatch.setattr(bot, "OWNER_ID", OWNER)
    return calls


def fake_claude(monkeypatch, responses):
    """Troca o subprocess.run: cada chamada consome uma resposta (returncode, stdout)."""
    commands = []

    def run(cmd, **kwargs):
        commands.append(cmd)
        code, stdout = responses.pop(0)
        return subprocess.CompletedProcess(cmd, code, stdout=stdout, stderr="falhou")

    monkeypatch.setattr(bot.subprocess, "run", run)
    return commands


def ok(result, session_id="sess-nova"):
    return 0, json.dumps({"result": result, "session_id": session_id, "is_error": False})


def message(text, chat_id=OWNER):
    return {"chat": {"id": int(chat_id)}, "text": text}


def sent_texts(calls):
    return [p["text"] for m, p in calls if m == "sendMessage"]


def test_wrong_chat_id_is_rejected(tg_calls, monkeypatch, capsys):
    commands = fake_claude(monkeypatch, [])
    bot.handle_message(message("oi", chat_id="999"))
    assert tg_calls == []
    assert commands == []
    assert "[lock] chat_id não autorizado: 999" in capsys.readouterr().out


def test_message_without_text_is_ignored(tg_calls, monkeypatch):
    fake_claude(monkeypatch, [])
    bot.handle_message({"chat": {"id": int(OWNER)}, "photo": []})
    bot.handle_message(None)
    assert tg_calls == []


def test_owner_message_goes_to_agent_and_saves_session(tg_calls, monkeypatch):
    commands = fake_claude(monkeypatch, [ok("resposta", "sess-1")])
    bot.handle_message(message("o que é rebase?"))
    assert sent_texts(tg_calls) == ["resposta"]
    assert commands[0][:3] == ["claude", "-p", "o que é rebase?"]
    assert "--resume" not in commands[0]
    assert bot.load_session() == "sess-1"


def test_existing_session_is_resumed(tg_calls, monkeypatch):
    bot.save_session("sess-velha")
    commands = fake_claude(monkeypatch, [ok("ok", "sess-velha")])
    bot.handle_message(message("salva isso"))
    assert commands[0][-2:] == ["--resume", "sess-velha"]


@pytest.mark.parametrize("command", ["/novo", "/reset", " /NOVO "])
def test_novo_clears_session(tg_calls, monkeypatch, command):
    bot.save_session("sess-1")
    commands = fake_claude(monkeypatch, [])
    bot.handle_message(message(command))
    assert bot.load_session() is None
    assert commands == []
    assert sent_texts(tg_calls) == ["🧹 Conversa reiniciada. A próxima mensagem começa do zero."]


def test_invalid_resume_restarts_from_scratch(tg_calls, monkeypatch):
    bot.save_session("sess-expirada")
    commands = fake_claude(monkeypatch, [(1, ""), ok("do zero", "sess-2")])
    reply = bot.ask_agent("oi")
    assert reply == "do zero"
    assert commands[0][-2:] == ["--resume", "sess-expirada"]
    assert "--resume" not in commands[1]
    assert bot.load_session() == "sess-2"


def test_timeout_returns_message(tg_calls, monkeypatch):
    def run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, bot.CLAUDE_TIMEOUT)

    monkeypatch.setattr(bot.subprocess, "run", run)
    assert "demorou demais" in bot.ask_agent("oi")


def test_long_reply_is_split(tg_calls, monkeypatch):
    long_reply = "a" * bot.TELEGRAM_MAX + "b" * bot.TELEGRAM_MAX + "c" * 10
    fake_claude(monkeypatch, [ok(long_reply)])
    bot.handle_message(message("me explica tudo"))
    parts = sent_texts(tg_calls)
    assert [len(p) for p in parts] == [bot.TELEGRAM_MAX, bot.TELEGRAM_MAX, 10]
    assert "".join(parts) == long_reply


def test_split_message_edges():
    assert bot.split_message("") == ["⚠️ (resposta vazia)"]
    assert bot.split_message("x" * bot.TELEGRAM_MAX) == ["x" * bot.TELEGRAM_MAX]


def test_allowed_tools_cover_claude_md_commands():
    """Toda chamada ao embed.py que o CLAUDE.md manda o agente rodar tem de casar
    com uma regra Bash(<prefixo>:*) do ALLOWED_TOOLS, senão o bot headless trava."""
    claude_md = (Path(bot.PROJECT_DIR) / "CLAUDE.md").read_text(encoding="utf-8")
    commands = re.findall(r"`([^`]*embed\.py[^`]*)`", claude_md)
    commands = [c for c in commands if "python" in c]  # ignora menções como `embed.py add`
    assert commands, "CLAUDE.md deveria mandar rodar o embed.py"
    prefixes = [m.group(1) for t in bot.ALLOWED_TOOLS if (m := re.fullmatch(r"Bash\((.*):\*\)", t))]
    for command in commands:
        assert any(command.startswith(p) for p in prefixes), command
