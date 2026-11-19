---
id: 20260201000072
title: "Variáveis de ambiente e export"
type: concept
tags: [linux, shell, variaveis-de-ambiente]
area: programacao
created: 01/02/26
source: agent
related: [20260201000071, 20260201000068]
---

## Definição
Variáveis de ambiente são pares `NOME=valor` que cada processo carrega e que são **herdados pelos processos filhos**. Programas as usam para configuração: `PATH`, `HOME`, `LANG`, `EDITOR`, credenciais e URLs de serviços.

## Como funciona
No shell existem dois tipos de variável: as **locais**, que só o próprio shell enxerga, e as **exportadas**, que vão para o ambiente dos comandos que ele inicia.

```bash
NOME="valor"          # variável local do shell
export NOME           # passa a ser herdada pelos filhos
export API_URL="https://api.exemplo.com"   # define e exporta
echo "$API_URL"
env | sort            # lista o ambiente
printenv HOME         # uma variável
unset API_URL         # remove
DEBUG=1 python app.py # define só para esse comando
```

Um processo filho recebe uma **cópia** do ambiente. Alterações feitas pelo filho não voltam para o pai. Por isso rodar um script que faz `export` (`./config.sh`) não altera o seu terminal, mas carregá-lo no shell atual com `source config.sh` (ou `. config.sh`) altera.

Onde definir para ser permanente, no bash:
- `~/.bashrc` — lido por shells interativos que não são de login (cada terminal aberto).
- `~/.profile` ou `~/.bash_profile` — lidos em shells de login.
- No zsh, os equivalentes são `~/.zshrc` e `~/.zprofile`.
- `/etc/environment` — para todos os usuários, só pares `NOME=valor`, sem sintaxe de shell.

Em Python:

```python
import os
url = os.environ.get("API_URL", "http://localhost")
os.environ["MODO"] = "teste"   # vale para este processo e os filhos que ele criar
```

Serviços iniciados pelo systemd ou pelo cron **não** leem o seu `.bashrc`, então variáveis definidas só ali não existem nesses contextos. Para projetos, é comum guardar variáveis num arquivo `.env` (fora do controle de versão) e carregá-lo com uma biblioteca ou com a diretiva `EnvironmentFile=` do systemd.

## Analogia
É como a mochila que uma criança recebe dos pais ao sair de casa: ela leva uma cópia do que estava lá, e o que ela trocar na própria mochila não muda a dos pais.

## Links
[[20260201000071-command-not-found-path]]
[[20260201000068-systemctl-systemd]]
