---
id: 20260201000011
title: "ModuleNotFoundError mesmo com o pacote instalado"
type: error
tags: [python, venv, pip, import]
area: programacao
created: 01/02/26
source: agent
related: [20260201000012]
---

## Erro
```
ModuleNotFoundError: No module named 'requests'
```

## Causa
Quase sempre o pacote foi instalado em um interpretador e o script roda em outro: o `pip` do sistema contra o `python` do ambiente virtual, ou vice-versa.

## Solução
```bash
python -m pip install requests   # instala no mesmo interpretador que vai rodar
which python                     # confere qual interpretador está ativo
python -c "import sys; print(sys.executable)"
```

## Contexto
Aparece ao esquecer de ativar o venv, ao usar o "Run" da IDE com outro interpretador selecionado, ou quando o nome do seu arquivo coincide com o do módulo (ex.: um `requests.py` local).

## Links
[[20260201000012-ambiente-virtual-venv-python]]
