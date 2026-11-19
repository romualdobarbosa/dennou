---
id: 20260201000068
title: "systemctl e serviços do systemd"
type: command
tags: [linux, systemd, servicos, systemctl]
area: programacao
created: 01/02/26
source: agent
related: [20260201000067, 20260201000076]
---

## O que faz
`systemctl` é a interface de linha de comando do systemd, o gerenciador de serviços e de inicialização da maioria das distribuições Linux atuais. Com ele você inicia, para, reinicia e habilita serviços para subirem no boot, e consulta o estado deles.

## Uso
```bash
systemctl status nginx
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl reload nginx        # recarrega configuração sem derrubar, se o serviço suportar
sudo systemctl enable nginx        # sobe automaticamente no boot
sudo systemctl enable --now nginx  # habilita e já inicia
sudo systemctl disable nginx
```

## Flags úteis
- `is-active` / `is-enabled` / `is-failed` — respostas curtas, boas para scripts.
- `list-units --type=service` — serviços carregados; `--failed` mostra só os que falharam.
- `daemon-reload` — relê os arquivos de unit depois de você editá-los.
- `cat nome` — mostra o arquivo de unit e os overrides em uso.
- `edit nome` — cria um override (drop-in) sem alterar o arquivo original do pacote.
- `mask` — impede totalmente que a unit seja iniciada, até manualmente.

## Exemplo
### Criando um serviço próprio
Um script Python que deve rodar continuamente e reiniciar se cair. Crie `/etc/systemd/system/coletor.service`:

```ini
[Unit]
Description=Coletor de métricas
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=coletor
WorkingDirectory=/opt/coletor
ExecStart=/opt/coletor/.venv/bin/python coletor.py
Restart=on-failure
RestartSec=5
Environment=LOG_LEVEL=info

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now coletor
systemctl status coletor
```

Pontos importantes:
- `[Unit]` descreve a unit e as dependências de ordem (`After=`) e de requisito (`Wants=`, `Requires=`).
- `[Service]` define como rodar. `ExecStart` precisa de caminho absoluto. `Restart=on-failure` reinicia se o processo sair com erro; `Restart=always` reinicia sempre.
- `[Install]` só é usado pelo `enable`: `WantedBy=multi-user.target` liga o serviço ao boot normal em modo texto ou servidor.
- Units do administrador ficam em `/etc/systemd/system/`; as instaladas por pacotes, em `/usr/lib/systemd/system/` (ou `/lib/systemd/system/` em algumas distros). Os arquivos em `/etc` têm precedência.
- Esquecer o `daemon-reload` depois de editar a unit faz o systemd continuar usando a versão antiga e avisar que o arquivo mudou no disco.

### Tipos de serviço e reinício
O campo `Type=` diz ao systemd como saber que o serviço terminou de subir. `simple` (padrão) considera o serviço pronto assim que o processo é iniciado; `exec` espera o executável ser carregado com sucesso; `forking` é para daemons antigos que se desligam do terminal criando um processo filho; `oneshot` é para tarefas que rodam e terminam, como um script de preparação, e costuma vir com `RemainAfterExit=yes`; `notify` espera o próprio programa avisar que está pronto. Se um serviço reinicia em loop, o systemd para de tentar depois de um número de falhas num intervalo (`StartLimitBurst` e `StartLimitIntervalSec`) e o marca como `failed`; `systemctl reset-failed nome` limpa esse estado.

### Lendo os logs
A saída padrão e de erro dos serviços vai para o journal:

```bash
journalctl -u coletor              # logs do serviço
journalctl -u coletor -f           # acompanha em tempo real
journalctl -u coletor --since "1 hour ago"
journalctl -b -p err               # erros desde o último boot
```

### Serviços de usuário e o linger
Nem todo serviço precisa de root. O systemd roda uma instância por usuário, controlada com `systemctl --user`, e as units ficam em `~/.config/systemd/user/`:

```bash
mkdir -p ~/.config/systemd/user
# crie ~/.config/systemd/user/bot.service com WantedBy=default.target
systemctl --user daemon-reload
systemctl --user enable --now bot
journalctl --user -u bot -f
```

Num serviço de usuário, o `[Install]` usa `WantedBy=default.target`, e não `multi-user.target`.

O problema clássico: a instância de usuário do systemd só existe enquanto o usuário tem uma sessão aberta. Ao fazer logout (ou fechar a última conexão SSH), os serviços de usuário são encerrados, e eles também não sobem no boot antes de alguém fazer login. A solução é habilitar o **linger** para esse usuário:

```bash
sudo loginctl enable-linger nome_do_usuario
loginctl show-user nome_do_usuario --property=Linger   # Linger=yes
```

Com linger ativo, o gerenciador do usuário é iniciado no boot e continua rodando depois do logout, então os serviços de usuário habilitados sobem sozinhos e permanecem ativos. `loginctl disable-linger` desfaz.

## Links
[[20260201000067-ps-kill-sinais]]
[[20260201000076-cron-crontab]]
