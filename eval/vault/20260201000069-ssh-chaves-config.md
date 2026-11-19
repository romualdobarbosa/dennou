---
id: 20260201000069
title: "SSH: chaves, ssh-copy-id e ~/.ssh/config"
type: command
tags: [linux, ssh, seguranca, remoto]
area: programacao
created: 01/02/26
source: agent
related: [20260201000070, 20260201000061]
---

## O que faz
O `ssh` abre um shell seguro em outra máquina. Autenticação por **par de chaves** é mais segura e prática que senha: a chave privada fica na sua máquina, e a chave pública é registrada no servidor em `~/.ssh/authorized_keys`.

## Uso
```bash
ssh usuario@servidor.exemplo.com
ssh -p 2222 usuario@servidor            # porta diferente
ssh -i ~/.ssh/chave_deploy usuario@servidor
```

## Flags úteis
- `ssh-keygen -t ed25519 -C "comentário"` — gera um par de chaves Ed25519 (recomendado atualmente).
- `ssh-copy-id usuario@servidor` — copia a chave pública para o `authorized_keys` do servidor com as permissões certas.
- `ssh-add ~/.ssh/id_ed25519` — carrega a chave no `ssh-agent`, para digitar a passphrase uma vez só.
- `-L 8080:localhost:80` — túnel: a porta 8080 local leva à porta 80 vista pelo servidor.
- `-v` / `-vvv` — modo verboso para diagnosticar falhas de conexão.
- `-J bastion` — conecta passando por um host intermediário.

## Exemplo
```bash
ssh-keygen -t ed25519 -C "notebook-trabalho"
# gera ~/.ssh/id_ed25519 (privada) e ~/.ssh/id_ed25519.pub (pública)
ssh-copy-id deploy@203.0.113.10
ssh deploy@203.0.113.10     # entra sem pedir a senha do servidor
```

Com o arquivo `~/.ssh/config`, dá para criar apelidos e não repetir opções:

```text
Host prod
    HostName 203.0.113.10
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
```

Depois disso, `ssh prod`, `scp arquivo prod:/tmp/` e `git clone prod:repo.git` usam essas configurações.

Boas práticas:
- Proteja a chave privada com passphrase e nunca a copie para servidores.
- Depois de confirmar que o acesso por chave funciona, desative login por senha no servidor (`PasswordAuthentication no` em `/etc/ssh/sshd_config`).
- Na primeira conexão, o ssh pede para confirmar a impressão digital do servidor e grava em `~/.ssh/known_hosts`. Se ela mudar depois, o aviso "REMOTE HOST IDENTIFICATION HAS CHANGED" pode indicar servidor reinstalado ou ataque; confirme antes de apagar a linha antiga.

## Links
[[20260201000070-ssh-permission-denied-publickey]]
[[20260201000061-chmod]]
