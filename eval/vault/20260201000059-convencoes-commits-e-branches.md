---
id: 20260201000059
title: "Convenções de commits e fluxo de branches"
type: note
tags: [git, commit, conventional-commits, workflow]
area: programacao
created: 01/02/26
source: agent
related: [20260201000041, 20260201000045]
---

## Título
Como organizar branches e escrever mensagens de commit num projeto Git.

## Conteúdo
### Fluxos de branches
Há dois modelos dominantes.

**Git Flow** usa branches de longa duração (`main` para o que está em produção e `develop` para integração) e branches de apoio (`feature/*`, `release/*`, `hotfix/*`). Funciona para software com versões numeradas e ciclos de release planejados, mas gera muitos merges e branches que vivem muito tempo e divergem.

**Trunk-based development** mantém um único branch principal (`main`), e todo trabalho vai em branches curtos, de horas ou poucos dias, integrados com frequência, quase sempre via pull request. Funcionalidades incompletas ficam escondidas atrás de feature flags em vez de esperar num branch. É o modelo mais comum em equipes que fazem deploy contínuo.

Em ambos, alguns hábitos ajudam:
- Nomeie branches com prefixo e descrição: `feature/login-oauth`, `fix/timeout-relatorio`.
- Atualize o branch com a base com frequência (`git pull --rebase` ou rebase sobre `origin/main`) para que os conflitos apareçam pequenos.
- Proteja o branch principal: push direto bloqueado, revisão obrigatória e CI passando antes do merge.
- Escolha uma estratégia de merge de pull request e mantenha: merge commit, squash ou rebase.

### Pull requests
Um pull request é o ponto de revisão antes da integração. Bons PRs são pequenos o bastante para serem revisados de uma vez, trazem uma descrição do problema e da solução, e indicam como testar. Revisões rápidas evitam que o branch envelheça e acumule conflitos. Quando o PR recebe ajustes depois da revisão, alguns times preferem commits novos durante a revisão e um squash no merge; outros reescrevem os commits do branch para que cada um continue fazendo sentido isoladamente.

### Commits pequenos e com propósito
Cada commit deveria representar **uma** mudança lógica que compila e passa nos testes. Isso facilita revisão, `git revert` de algo específico e `git bisect`. Use `git add -p` para escolher, trecho a trecho, o que entra em cada commit quando você mexeu em coisas diferentes no mesmo arquivo.

### Mensagens de commit
Convenções amplamente adotadas:
- Linha de assunto curta, idealmente até cerca de **50 caracteres**, sem ponto final.
- Linha em branco entre o assunto e o corpo.
- Corpo quebrado em cerca de **72 caracteres** por linha, explicando o **porquê** da mudança; o diff já mostra o quê.
- Assunto no imperativo: "adiciona validação de CPF", e não "adicionado" ou "adicionando". O próprio Git escreve assim ("Merge branch...", "Revert ...").

```text
corrige cálculo de frete para CEPs de outro estado

A tabela de faixas era consultada com o CEP sem o hífen removido,
o que fazia cair sempre na faixa padrão.
```

### Conventional Commits
A especificação Conventional Commits padroniza o assunto no formato `tipo(escopo opcional): descrição`:

```text
feat(api): adiciona endpoint de exportação CSV
fix: trata divisão por zero no relatório
docs: atualiza instruções de instalação
refactor(auth): extrai validação de token
test: cobre caso de carrinho vazio
chore: atualiza dependências
```

Os tipos `feat` e `fix` são definidos pela especificação; os demais (`docs`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`, `style`) são convenção comum. A vantagem é que ferramentas conseguem ler o histórico, gerar changelog automaticamente e decidir o próximo número de versão.

### Mudanças incompatíveis e versionamento semântico
A especificação liga os commits ao versionamento semântico (SemVer, `MAJOR.MINOR.PATCH`):
- `fix` corresponde a uma versão **PATCH** (1.4.2 → 1.4.3).
- `feat` corresponde a uma versão **MINOR** (1.4.2 → 1.5.0).
- Uma **mudança incompatível** (breaking change), de qualquer tipo, corresponde a uma versão **MAJOR** (1.4.2 → 2.0.0).

A mudança incompatível é sinalizada de duas formas, que podem ser usadas juntas: um `!` logo antes dos dois-pontos, ou um rodapé `BREAKING CHANGE:` no fim da mensagem, depois de uma linha em branco.

```text
feat(api)!: remove suporte ao parâmetro "formato"

BREAKING CHANGE: o endpoint /exportar agora aceita só o parâmetro "tipo".
Clientes que enviam "formato" recebem erro 400.
```

Ferramentas como semantic-release e release-please usam essas marcações para gerar a versão e as notas de release sem intervenção manual.

## Links
[[20260201000041-git-commit-amend]]
[[20260201000045-git-rebase]]
