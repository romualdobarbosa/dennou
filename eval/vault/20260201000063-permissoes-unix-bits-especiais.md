---
id: 20260201000063
title: "Permissões Unix: rwx, umask e bits especiais"
type: concept
tags: [linux, permissoes, seguranca]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000061, 20260201000062, 20260201000080]
---

## Definição
Todo arquivo e diretório no Linux tem um dono, um grupo e três conjuntos de permissões: para o **dono** (user), para o **grupo** (group) e para **os outros** (others). Cada conjunto combina leitura (`r`), escrita (`w`) e execução (`x`). Além disso, existem três bits especiais: setuid, setgid e sticky.

## Como funciona
### Lendo o ls -l
```text
-rwxr-x--- 1 ana devs 2048 jan 10 09:00 deploy.sh
drwxr-xr-x 2 ana devs 4096 jan 10 09:00 docs
```
O primeiro caractere é o tipo (`-` arquivo, `d` diretório, `l` link simbólico). Depois vêm três trincas: `rwx` para o dono `ana`, `r-x` para o grupo `devs`, `---` para os outros.

### O que rwx significa em diretórios
Para arquivos, o significado é intuitivo. Para diretórios, é diferente:
- `r` — listar os nomes das entradas (`ls`).
- `w` — criar, renomear e apagar entradas dentro do diretório. Atenção: apagar um arquivo depende da permissão de escrita **no diretório**, não no arquivo.
- `x` — atravessar o diretório: entrar nele com `cd` e acessar arquivos pelo caminho. Sem `x`, nem um arquivo com permissão de leitura lá dentro pode ser aberto.

### Notação octal
Cada permissão vale um bit: r=4, w=2, x=1. Somando, cada trinca vira um dígito de 0 a 7. `754` é `rwxr-xr--`. As combinações mais comuns:
- `644` — arquivos comuns.
- `755` — executáveis e diretórios.
- `600` — arquivos privados, como chaves SSH.
- `700` — diretórios privados.

### umask
A `umask` define quais permissões são **retiradas** de arquivos e diretórios novos. Arquivos nascem a partir de 666 e diretórios a partir de 777, menos os bits da umask. Com a umask comum `022`, arquivos novos ficam `644` e diretórios `755`. Com `077`, nada fica acessível para grupo e outros.

```bash
umask          # mostra a atual, por exemplo 0022
umask 027      # para a sessão atual
```

### Root e a ordem da verificação
O kernel verifica apenas **uma** trinca: se você é o dono, valem as permissões do dono, mesmo que as do grupo sejam mais generosas. Se não for o dono mas pertencer ao grupo, valem as do grupo. Caso contrário, as dos outros. O root ignora as permissões de leitura e escrita.

### Bits especiais: setuid, setgid e sticky
Um quarto dígito octal, à esquerda dos outros três, controla os bits especiais: setuid vale 4, setgid vale 2 e sticky vale 1.

**setuid (4)** em um executável faz o programa rodar com os privilégios do **dono do arquivo**, e não de quem o executou. O exemplo clássico é o `/usr/bin/passwd`: ele pertence ao root e tem setuid, para que um usuário comum consiga alterar a própria senha gravando em `/etc/shadow`. No `ls -l` aparece como `s` no lugar do `x` do dono: `-rwsr-xr-x`. Por motivos de segurança, o Linux ignora setuid em scripts interpretados.

**setgid (2)** em executável faz rodar com o grupo do arquivo. Em **diretório**, tem um uso muito prático: arquivos criados lá dentro **herdam o grupo do diretório**, e não o grupo principal de quem criou. É o jeito clássico de montar uma pasta de equipe:

```bash
sudo chgrp devs /srv/projeto
sudo chmod 2775 /srv/projeto      # ou: chmod g+s /srv/projeto
```

**sticky bit (1)** em um diretório faz com que só o dono do arquivo (ou o dono do diretório, ou o root) possa apagar ou renomear o arquivo, mesmo que outros tenham permissão de escrita no diretório. É o que protege o `/tmp`, onde todos escrevem mas ninguém apaga os arquivos dos outros. O `/tmp` aparece como `drwxrwxrwt`; o `t` no fim é o sticky bit.

```bash
chmod 1777 /srv/compartilhado     # ou: chmod +t /srv/compartilhado
chmod u+s programa                # setuid
```

Quando o bit especial está ligado mas o `x` correspondente não, a letra aparece em maiúscula: `S` para setuid/setgid e `T` para sticky. Normalmente isso indica uma configuração sem sentido.

## Analogia
As permissões são as chaves de um prédio: cada morador tem chave do próprio apartamento, a portaria abre o hall para quem é do condomínio, e o público só vê a fachada. O sticky bit é o depósito comum, onde qualquer um deixa suas caixas, mas só o dono de cada caixa pode tirá-la de lá.

## Links
[[20260201000061-chmod]]
[[20260201000062-chown]]
[[20260201000080-sudo-visudo]]
