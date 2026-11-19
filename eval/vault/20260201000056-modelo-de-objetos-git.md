---
id: 20260201000056
title: "Modelo de objetos do Git: blobs, trees, commits e tags"
type: concept
tags: [git, internals, hash]
area: ciencia-da-computacao
created: 01/02/26
source: agent
related: [20260201000049, 20260201000058]
---

## Definição
Internamente, o Git é um banco de dados **endereçado por conteúdo**: cada objeto é guardado sob o hash do seu próprio conteúdo. Existem quatro tipos de objeto (blob, tree, commit e tag anotada), e branches, tags e o HEAD são apenas nomes que apontam para esses hashes.

## Como funciona
### Os quatro objetos
- **Blob** — o conteúdo bruto de um arquivo, sem nome nem permissões. Dois arquivos idênticos em pastas diferentes viram um único blob.
- **Tree** — uma listagem de diretório: para cada entrada, o modo (permissões), o tipo, o hash e o nome. Trees apontam para blobs e para outras trees.
- **Commit** — aponta para uma tree (o snapshot da raiz do projeto), para zero ou mais commits pais, e guarda autor, committer, datas e mensagem. Um commit inicial não tem pai; um commit de merge tem dois ou mais.
- **Tag anotada** — aponta para um objeto (normalmente um commit) e guarda nome, autor, data e mensagem. Tags leves (`git tag v1`) não criam objeto: são só uma referência.

Como o hash de um commit cobre a tree e os pais, alterar qualquer coisa no passado muda o hash de todos os commits seguintes. É por isso que `rebase` e `--amend` produzem commits "novos".

### Explorando os objetos
```bash
git cat-file -t a1b2c3d       # tipo do objeto (commit, tree, blob, tag)
git cat-file -p a1b2c3d       # conteúdo legível
git cat-file -p HEAD^{tree}   # a tree raiz do commit atual
echo "olá" | git hash-object --stdin   # calcula o hash que esse conteúdo teria
git ls-tree -r HEAD           # todos os arquivos do snapshot com seus blobs
```

### Onde ficam
Objetos novos são gravados como arquivos individuais comprimidos com zlib (objetos "soltos", ou loose objects) em `.git/objects/`, numa pasta com os dois primeiros caracteres do hash, por exemplo `.git/objects/a1/b2c3d...`. Periodicamente, ou ao rodar `git gc`, o Git os reúne em **packfiles** (`.git/objects/pack/`), que armazenam objetos parecidos como deltas uns dos outros. Isso explica por que repositórios com muito histórico ocupam pouco espaço.

### Referências
- Branches são arquivos (em `.git/refs/heads/` ou consolidados em `.git/packed-refs`) contendo apenas o hash do commit da ponta.
- `HEAD` normalmente é uma referência simbólica: o arquivo `.git/HEAD` contém algo como `ref: refs/heads/main`. Em detached HEAD, contém um hash direto.
- Branches remotos ficam em `refs/remotes/origin/...`.

Fazer um commit é, em essência: gravar blobs dos arquivos staged, gravar as trees, gravar o objeto commit apontando para a tree raiz e para o pai, e atualizar o arquivo do branch atual com o novo hash.

### Objetos inalcançáveis
Um commit que nenhuma referência alcança (depois de um `reset --hard`, por exemplo) não é apagado na hora. Ele continua no banco de objetos até que o reflog expire e o `git gc` faça a limpeza. `git fsck --lost-found` lista objetos soltos assim.

### O hash: SHA-1 e a transição para SHA-256
Por padrão, os hashes do Git são SHA-1 (40 caracteres hexadecimais). Depois da primeira colisão prática de SHA-1 publicada em 2017 (o ataque "SHAttered"), o Git passou a usar, a partir da versão 2.13, uma implementação de SHA-1 com detecção de colisão (SHA-1DC), que rejeita os padrões conhecidos de ataque.

A solução de longo prazo é trocar o algoritmo. Desde o **Git 2.29** é possível criar repositórios que usam **SHA-256** (hashes de 64 caracteres):

```bash
git init --object-format=sha256 meu-repo
git rev-parse --show-object-format     # mostra sha1 ou sha256
```

O formato de um repositório é definido na criação. A interoperabilidade entre repositórios SHA-1 e SHA-256 ainda é limitada, e boa parte das plataformas de hospedagem não aceita repositórios SHA-256, então o uso prático continua restrito a cenários controlados.

## Analogia
É como um depósito em que cada caixa recebe como etiqueta uma impressão digital do seu conteúdo. Para saber se algo já está guardado, basta calcular a impressão digital. O commit é uma ficha que diz "a caixa-raiz do projeto nesse momento é esta, e a ficha anterior é aquela".

## Links
[[20260201000049-git-reflog]]
[[20260201000058-git-fetch-vs-pull]]
