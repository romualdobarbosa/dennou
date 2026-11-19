---
id: 20260201000012
title: "Ambientes virtuais com venv"
type: command
tags: [python, venv, pip, dependencias]
area: programacao
created: 01/02/26
source: agent
related: [20260201000011]
---

## O que faz
O módulo `venv` cria um diretório com um interpretador Python isolado e seu próprio `site-packages`. Pacotes instalados ali não afetam o Python do sistema nem outros projetos, o que evita conflito de versões entre projetos diferentes.

## Uso
```bash
python3 -m venv .venv            # cria o ambiente na pasta .venv
source .venv/bin/activate        # ativa (Linux/macOS, bash/zsh)
.venv\Scripts\activate           # ativa (Windows)
deactivate                       # sai do ambiente
```

## Flags úteis
- `--prompt nome` — muda o nome exibido no prompt quando ativo.
- `--system-site-packages` — deixa o ambiente enxergar pacotes instalados no Python do sistema.
- `--clear` — apaga o conteúdo de um ambiente existente antes de recriar.
- `--upgrade-deps` — atualiza `pip` (e `setuptools` em versões antigas) logo na criação.

## Exemplo
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install requests
python -m pip freeze > requirements.txt
# em outra máquina:
python -m pip install -r requirements.txt
```

Ativar não é obrigatório: dá pra chamar o interpretador direto, por exemplo `.venv/bin/python script.py`. Isso é útil em cron, systemd e scripts, onde não existe shell interativo para rodar o `activate`.

Boas práticas:
- Não versione a pasta do ambiente; coloque `.venv/` no `.gitignore`.
- O ambiente guarda caminhos absolutos: mover ou renomear a pasta quebra os scripts dentro de `bin/`. Recrie em vez de mover.
- Para saber se um ambiente está ativo, confira `sys.prefix` (aponta para a pasta do venv) ou a variável de ambiente `VIRTUAL_ENV`, definida pelo `activate`.
- Ferramentas como `uv` e `poetry` criam e gerenciam o venv automaticamente, mas o resultado continua sendo um ambiente virtual comum.

## Links
[[20260201000011-modulenotfounderror-python]]
