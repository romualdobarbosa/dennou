---
id: 20260201000070
title: "Erro SSH: Permission denied (publickey)"
type: error
tags: [linux, ssh, permissoes]
area: programacao
created: 01/02/26
source: agent
related: [20260201000069, 20260201000061]
---

## Erro
```
usuario@servidor: Permission denied (publickey).
```

## Causa
O servidor só aceita chave e nenhuma chave oferecida foi aceita. Causas comuns: chave pública ausente no `authorized_keys`, usuário errado, chave errada sendo oferecida ou permissões frouxas demais, que fazem o `sshd` ignorar os arquivos (opção `StrictModes`).

## Solução
```bash
ssh -v usuario@servidor               # mostra quais chaves foram tentadas
# no servidor:
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
# no cliente:
chmod 600 ~/.ssh/id_ed25519
ssh -i ~/.ssh/id_ed25519 usuario@servidor
```

## Contexto
Também acontece se o diretório home do usuário no servidor tiver escrita para grupo ou outros. Os logs do servidor (`journalctl -u sshd` ou `/var/log/auth.log`) costumam dizer o motivo exato.

## Links
[[20260201000069-ssh-chaves-config]]
[[20260201000061-chmod]]
