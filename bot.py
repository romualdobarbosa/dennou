#!/usr/bin/env python3
"""
Bot do Telegram para o dennou.

Recebe mensagens no Telegram, repassa para o agente Claude Code headless
(`claude -p`), que segue o CLAUDE.md (busca no vault, responde e salva nota
quando pedido), e devolve a resposta. Travado pelo chat_id do dono.

Long polling via stdlib (sem dependências novas). Roda no próprio PC para
salvar as notas localmente.
"""

import contextlib
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.resolve()

# Permissões do agente headless (`claude -p` não pode pedir confirmação, então
# tudo que não está liberado é negado). Mesmo travado por chat_id, o agente só
# roda o embed.py e só mexe em arquivos do vault.
#
# TOOLS: as únicas ferramentas que existem na sessão (sem Glob, Grep, WebFetch...).
TOOLS = "Bash,Read,Edit,Write"
# ALLOWED_TOOLS: o que roda sem confirmação.
# - A regra de Bash casa por prefixo, então tem de bater com o comando que o
#   CLAUDE.md manda rodar (`.venv/bin/python3 embed.py ...`).
# - Caminhos com `./` são relativos ao diretório do projeto. `Edit(...)` vale
#   também pro Write. Ler ou escrever fora do repo é negado.
ALLOWED_TOOLS = [
    "Bash(.venv/bin/python3 embed.py:*)",
    "Read(./vault/**)",
    "Read(./SCHEMA.md)",
    "Read(./TAGS.md)",
    "Edit(./vault/**)",
]
# DISALLOWED_TOOLS: o Claude Code deixa ler qualquer arquivo dentro do diretório
# de trabalho sem pedir, então os segredos do projeto são negados explicitamente.
DISALLOWED_TOOLS = [
    "Read(./.env)",
    "Read(./.bot_session)",
    "Edit(./.env)",
]

CLAUDE_TIMEOUT = 300  # segundos por mensagem
TELEGRAM_MAX = 4096  # limite de caracteres por mensagem do Telegram
POLL_TIMEOUT = 60  # long polling: quanto o getUpdates segura a conexão

# Guarda o session_id da conversa para dar continuidade entre mensagens
# (sem isso cada `claude -p` começa do zero e "salva isso" perde o contexto).
SESSION_FILE = PROJECT_DIR / ".bot_session"


def load_session() -> str | None:
    """Lê o session_id salvo, se houver."""
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text().strip() or None
    return None


def save_session(session_id: str) -> None:
    if session_id:
        SESSION_FILE.write_text(session_id)


def clear_session() -> None:
    SESSION_FILE.unlink(missing_ok=True)


def load_env(path: Path) -> None:
    """Carrega KEY=VALUE de um .env simples para o os.environ."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


TOKEN: str | None = None
OWNER_ID: str | None = None
MODEL = "sonnet"
API = ""


def configure(env_file: Path = PROJECT_DIR / ".env") -> None:
    """Lê o .env e as variáveis de ambiente. Fica fora do import pra os testes
    não carregarem o .env de verdade."""
    global TOKEN, OWNER_ID, MODEL, API
    load_env(env_file)
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    OWNER_ID = os.environ.get("TELEGRAM_OWNER_ID")
    MODEL = os.environ.get("DENNOU_BOT_MODEL", "sonnet")
    API = f"https://api.telegram.org/bot{TOKEN}"


def tg(method: str, **params):
    """Chama a API do Telegram via POST (urllib) e devolve o JSON da resposta.

    POST (em vez de GET) porque respostas longas estouram o limite de tamanho
    de URL. urllib já define o Content-Type form-urlencoded quando há `data`.
    """
    url = f"{API}/{method}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=POLL_TIMEOUT + 10) as resp:
        payload = json.load(resp)
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API {method} falhou: {payload.get('description')}")
    return payload


def split_message(text: str) -> list[str]:
    """Quebra o texto em pedaços de até TELEGRAM_MAX caracteres."""
    text = text or "⚠️ (resposta vazia)"
    return [text[i : i + TELEGRAM_MAX] for i in range(0, len(text), TELEGRAM_MAX)]


def send(chat_id, text: str) -> None:
    """Envia texto ao usuário, quebrando em pedaços se passar do limite."""
    for part in split_message(text):
        tg("sendMessage", chat_id=chat_id, text=part)


def _run_claude(message: str, session_id: str | None):
    """Roda o `claude -p`, retomando `session_id` se houver. Devolve o proc
    ou None em timeout."""
    cmd = [
        "claude",
        "-p",
        message,
        "--output-format",
        "json",
        "--model",
        MODEL,
        "--tools",
        TOOLS,
        "--allowedTools",
        *ALLOWED_TOOLS,
        "--disallowedTools",
        *DISALLOWED_TOOLS,
    ]
    if session_id:
        cmd += ["--resume", session_id]
    try:
        return subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None


def ask_agent(message: str) -> str:
    """Repassa a mensagem ao Claude headless, mantendo a sessão entre mensagens,
    e devolve o texto da resposta."""
    session_id = load_session()
    proc = _run_claude(message, session_id)

    # Resume de uma sessão velha/inválida falha -> recomeça do zero uma vez.
    if session_id and proc is not None and proc.returncode != 0:
        print("[session] resume falhou; iniciando sessão nova", flush=True)
        clear_session()
        proc = _run_claude(message, None)

    if proc is None:
        return "⏱️ O agente demorou demais e foi interrompido."
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout)[-500:]
        return f"⚠️ Erro ao chamar o agente:\n{detail}"

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.stdout.strip() or "⚠️ Resposta vazia do agente."

    if data.get("session_id"):
        save_session(data["session_id"])

    if data.get("is_error"):
        return f"⚠️ O agente retornou erro: {data.get('result', 'sem detalhe')}"
    return data.get("result", "").strip()


def handle_message(msg: dict) -> None:
    """Trata uma mensagem do Telegram: trava pelo chat_id, /novo e repasse ao agente."""
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    if str(chat_id) != str(OWNER_ID):
        print(f"[lock] chat_id não autorizado: {chat_id}", flush=True)
        return
    text = msg["text"]
    print(f"[msg] {text[:80]}", flush=True)
    if text.strip().lower() in ("/novo", "/reset"):
        clear_session()
        send(chat_id, "🧹 Conversa reiniciada. A próxima mensagem começa do zero.")
        return
    try:
        tg("sendChatAction", chat_id=chat_id, action="typing")
        reply = ask_agent(text)
        send(chat_id, reply)
    except Exception as e:  # noqa: BLE001
        print(f"[handler] erro: {e}", flush=True)
        with contextlib.suppress(Exception):
            send(chat_id, f"⚠️ Erro interno: {e}")


def main() -> None:
    configure()
    if not TOKEN or not OWNER_ID:
        sys.exit("Defina TELEGRAM_BOT_TOKEN e TELEGRAM_OWNER_ID no .env (veja .env.example).")

    print(f"dennou-bot iniciado. modelo={MODEL} dono={OWNER_ID}", flush=True)
    offset = None
    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            updates = tg("getUpdates", **params)
        except Exception as e:  # noqa: BLE001 — polling não pode morrer
            print(f"[polling] erro: {e}; tentando de novo em 5s", flush=True)
            time.sleep(5)
            continue

        for upd in updates.get("result", []):
            offset = upd["update_id"] + 1
            handle_message(upd.get("message") or upd.get("edited_message"))


if __name__ == "__main__":
    main()
