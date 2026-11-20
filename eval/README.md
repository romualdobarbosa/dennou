# Dataset de eval de retrieval

Eu queria medir se a busca semântica do dennou acha a nota certa, e pra isso não dá pra usar o meu vault real, que é privado. Então montei um vault sintético e público, com perguntas rotuladas à mão, pra servir de gabarito.

## O que tem aqui

- `vault/`: 80 notas em português, no mesmo formato do `SCHEMA.md` (frontmatter completo, body pelo template do tipo, `## Links` batendo com o `related`). São 20 notas de cada tema (Python, SQL, Git e Linux), com ids sintéticos de `20260201000001` a `20260201000080`.
- `queries.jsonl`: 60 perguntas, uma por linha, no formato abaixo.
- `manifest.json`: contagens, lista das notas longas e das perguntas cuja resposta está no fim delas.
- `validate_dataset.py`: confere a estrutura de tudo isso (só stdlib).

```json
{"id": "q001", "query": "...", "kind": "literal", "relevant": {"20260201000022": 2, "20260201000040": 1}}
```

## Como as notas foram escritas

Todo o conteúdo é técnico e conferido, sem nada pessoal. Os tamanhos variam de propósito. São 48 notas curtas (até umas 150 palavras), 20 médias (250 a 400) e 12 longas (de 620 a 700 palavras).

As notas longas existem pra expor um limite conhecido. O modelo de embedding trunca a entrada em 128 tokens, então, indexando a nota inteira, tudo que vem depois disso some do vetor (foi por isso que a produção passou a indexar em chunks). Em cada nota longa, uma informação específica aparece só no trecho final, sempre depois de umas 400 palavras. Tipo o nível de isolamento padrão do MySQL, no fim da nota de transações, ou o `loginctl enable-linger`, no fim da nota de systemd. As 12 perguntas listadas em `tail_answer_queries` só têm resposta nesses trechos.

Também coloquei pares de notas fáceis de confundir, pra busca não ficar trivial. Por exemplo `git reset`, `git revert` e `git restore`, WHERE e HAVING, lista e tupla, `chmod` e `chown`.

O campo `related` de cada nota aponta pra notas realmente relacionadas dentro desse vault, então dá pra usar ele como experimento também.

## A rubrica

Cada pergunta lista as notas relevantes com um grau. Nota que não aparece vale 0.

- **2**: a nota responde a pergunta. Normalmente é uma só, no máximo duas. Em "qual a diferença entre WHERE e HAVING no SQL", as notas de WHERE e de HAVING levam 2.
- **1**: a nota é do mesmo assunto e dá contexto útil, mas não responde sozinha. Na mesma pergunta, a nota de GROUP BY e a da ordem lógica de execução do SELECT levam 1.
- **0**: irrelevante. A nota de `git stash`, na pergunta sobre WHERE e HAVING.

## Distribuição das perguntas

| kind | qtd | o que testa |
|---|---|---|
| `literal` | 25 | pergunta usando o vocabulário da nota |
| `paraphrase` | 15 | pergunta de iniciante, evitando de propósito as palavras do título e do corpo |
| `cross_lingual` | 10 | pergunta em inglês, nota em português |
| `no_answer` | 10 | nada no vault responde (`relevant` vazio) |

As `no_answer` misturam coisas de fora (receita de pão de queijo) com coisas quase no tema, como Docker, Rust, Git LFS e `groupby` do pandas, pra ver se a busca devolve falso positivo com score alto.

## Viés conhecido

Fui eu (com ajuda de um agente) que escrevi as notas e as perguntas, então as perguntas tendem a usar o mesmo jeito de falar das notas. Isso deixa o `literal` mais fácil do que seria com perguntas de outra pessoa. As paráfrases e as perguntas em inglês existem pra diminuir esse efeito, mas não eliminam. Os números do eval valem pra comparar versões do retrieval entre si, não como medida absoluta.

## Como validar

```bash
python3 eval/validate_dataset.py
```

Ele confere as contagens, o frontmatter, se os ids batem com os nomes dos arquivos, se todo id citado em `relevant` e `related` existe, a distribuição por kind e se toda pergunta com resposta tem pelo menos uma nota com grau 2.

## Como rodar o eval

```bash
make eval         # as 12 configs e os experimentos do related, da seção Links e da busca híbrida, grava em eval/results/
make eval-quick   # gate do CI, 10 perguntas fixas com a config de produção
uv run python -m eval.run_generation_eval   # eval de geração, modo controlado (claude -p)
uv run python -m eval.run_agent_eval        # eval de geração, modo agente (claude -p)
```

O `make eval` roda tudo em CPU (dá pra trocar com `uv run python -m eval.run_eval --device cuda`) e baixa o e5-small e o bge-m3 na primeira vez, uns 2,5 GB no cache do Hugging Face. Cada config indexa `eval/vault` num Chroma temporário, com distância cosseno igual à produção, e nunca encosta no vault real nem no `chroma_db/`. Os resultados ficam em `eval/results/<config>.json`, com as métricas, a curva de threshold, o top-5 de cada pergunta e os metadados da rodada (modelo, `max_seq_length`, chunking, commit, CPU, versão do torch). A tabela comparativa sai em `eval/results/summary.md`.

As configs cruzam três modelos (o `paraphrase-multilingual-MiniLM-L12-v2` de produção, o `intfloat/multilingual-e5-small` com os prefixos `query: ` e `passage: ` que ele exige, e o `BAAI/bge-m3`), nota inteira contra chunks, e texto com e sem o título. A config `minilm-chunk-title` é a de produção (antes era `minilm-whole-title`, uma nota inteira por vetor). O harness não tem cópia da lógica de produção. Ele chama as funções do `embed.py` pra ler a nota, quebrar em chunks (`note_chunks`), gravar no Chroma (`index_note`), juntar os chunks por nota (`best_chunk_per_note`) e calcular o score, e o corte vem do mesmo `SCORE_THRESHOLD`. Conferi que o top-5 dela bate com o `embed.py search` nas 60 perguntas.

### Chunks

O chunking é o do `embed.py`, o mesmo da produção. Antes de quebrar, ele tira a seção `## Links` do corpo (vale também pro modo nota inteira, veja abaixo). Os chunks juntam parágrafos seguidos (sem partir bloco de código) até 256 tokens, ou até o `max_seq_length` do modelo se ele for menor, contando prefixo, título e tokens especiais. No MiniLM isso dá 128, então nenhum chunk é cortado. Parágrafo que sozinho não cabe vira janelas de palavras com 20% de sobreposição. O score da nota é o maior score entre os chunks dela, e cada nota aparece uma vez só no ranking.

### Métricas

Só as 50 perguntas com resposta entram em recall, MRR e nDCG. As 10 `no_answer` servem pro threshold.

- Recall@k vale 1 se pelo menos uma nota de grau 2 aparece no top-k. Quando a pergunta tem duas notas de grau 2 (WHERE e HAVING, por exemplo), achar uma já conta.
- MRR é a média de 1/posição da primeira nota de grau 2 no top-10.
- nDCG@5 usa ganho igual ao grau (2 ou 1), desconto log2(posição + 1), normalizado pelo ranking ideal das notas rotuladas.
- Latência é o p50 e o p95 de encode da pergunta mais a consulta no Chroma, depois de uma chamada de aquecimento. Indexação é o tempo total de encode e upsert das 80 notas, sem contar o carregamento do modelo.

Também separo o Recall@5 das 12 perguntas de cauda, as do `tail_answer_queries`.

### Threshold

O search marca as notas com score abaixo de 0.55 (`DENNOU_SCORE_THRESHOLD`, que antes era 0.4). Até 20/11/2026 o agente ignorava essas notas, e hoje o score é só uma pista pra ele (veja o eval de geração, abaixo). Pra cada config calculo uma curva de 0.0 a 1.0, de 0.05 em 0.05. Num eixo fica o falso positivo, que é a fração das perguntas `no_answer` cujo top-1 passa do threshold (o agente usaria uma nota que não responde nada). No outro fica o Recall@5 das perguntas com resposta contando só as notas acima do threshold. O threshold sugerido é o de maior recall com falso positivo de no máximo 10% (no empate, o menor falso positivo e depois o threshold mais alto). Com só 10 perguntas sem resposta, cada uma vale 10 pontos de falso positivo, então trate esse número como indicação e não como valor exato. O score muda de escala entre modelos (no e5 tudo fica acima de 0.7), por isso o threshold não passa de um modelo pro outro.

### Expansão pelo related

Na melhor config por nDCG@5, as notas listadas no `related` das top-3 entram com score max(score próprio, λ × score da nota de origem), e a lista é reordenada. Com λ = 1 a relacionada fica logo atrás da origem. Rodo λ = 0.8, 0.9 e 1.0. Na rodada atual (em `bge-m3-chunk-notitle`) nenhum λ melhora o Recall@5 e o λ = 1.0 piora. Numa rodada anterior, com a seção `## Links` ainda embedada, a melhor config era a `bge-m3-chunk-title` e o λ = 1.0 subia o Recall@5 de 0.900 pra 0.940, mas o λ foi escolhido nas mesmas perguntas em que foi medido. Não adotei, e a busca não usa o `related`.

### Seção `## Links`

Toda nota termina com `## Links`, os wiki-links do Obsidian pras notas relacionadas. Isso é navegação, não conteúdo, e embedado vira texto feito de nomes de arquivo de outras notas. O experimento roda a config de produção de novo com a seção invertida (com, se a produção tira; sem, se a produção mantém) e grava `eval/results/links_section.json`. Sem a seção, o Recall@5 foi de 0.940 pra 0.960 (uma pergunta em inglês a mais no top-5), o nDCG@5 de 0.819 pra 0.832, e o falso positivo em 0.55 ficou em 10%. Adotei, com `embed.KEEP_LINKS_SECTION = False`, e o eval inteiro usa o mesmo texto que a produção.

### Busca híbrida e rerank

Queria saber se dava pra melhorar a busca de produção sem trocar o modelo. O experimento roda em cima do ranking vetorial da `minilm-chunk-title` e grava `eval/results/hybrid_rerank.json`. Testei BM25 sozinho (lexical, sobre título e corpo da nota, sem `## Links`), duas fusões com o vetorial (RRF com k = 60, e a soma a × cosseno + (1 − a) × BM25 normalizado, com a = 0.5, 0.7 e 0.9) e o rerank do top-20 com dois cross-encoders multilíngues, o `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` e o `BAAI/bge-reranker-v2-m3`. O corte continua no cosseno de produção, então o falso positivo em 0.55 fica em 10% em todas as variantes.

A soma com a = 0.7 sobe o Recall@1 de 0.720 pra 0.860 e o MRR de 0.802 pra 0.896, quase de graça (0,1 ms a mais por busca). Em troca ela perde a q043 do top-5, uma pergunta em inglês, porque o BM25 não ajuda quando a pergunta e a nota estão em línguas diferentes, e o Recall@5 cai de 0.960 pra 0.940. O `bge-reranker-v2-m3` foi o melhor em tudo (Recall@5 0.980, MRR 0.918), mas leva uns 58 s por busca em CPU. O mMiniLM leva uns 4,5 s e ainda perde uma pergunta de cauda.

Só que o Recall@5 contando só as notas acima de 0.55 ficou em 0.740 em todas as variantes, porque mudar a ordem não muda quais notas passam do corte. Usar o score da soma como corte também não ajudou (de 0.580 a 0.700 no threshold sugerido). O agente lê todas as notas que passam do corte, então subir a nota certa de 3º pra 1º muda pouco pra ele. Não adotei nenhuma variante. O gargalo é o corte (a nota certa está no top-5 em 96% das perguntas, mas passa de 0.55 em 74%), e é por ele que quero seguir.

### Eval de geração

O eval de retrieval para no top-5. Ele dizia que a nota certa estava ali em 96% das perguntas, mas passava de 0.55 em 74%, e o agente ignorava o que ficava abaixo. Faltava medir a outra ponta, se o agente usa a nota certa e se a resposta é fiel a ela. São dois scripts, os dois chamam o `claude -p` (pela assinatura, sem chave de API), o Sonnet responde e o Opus julga se a resposta está correta e se o que ela atribui à nota está mesmo na nota. Cada chamada fica em cache, então rodar de novo só faz o que falta.

O primeiro, `run_generation_eval.py`, é o modo controlado. A busca roda dentro do script, as notas que a variante deixa passar vão inteiras no prompt e o modelo responde sem ferramentas, devolvendo a resposta e os ids das notas que usou. Testei três regras nas 60 perguntas, e os resultados ficam em `eval/results/generation/`.

| regra | nota certa no prompt | citou nota certa | fiel | falso positivo | prompt médio |
|---|---|---|---|---|---|
| A: só notas ≥ 0.55 (a regra de antes) | 74% | 74% | 98% | 0 de 10 | 3.706 caracteres |
| B: ≥ 0.55, mais uma faixa "talvez" de 0.45 a 0.55 | 84% | 84% | 100% | 0 de 10 | 6.130 caracteres |
| C: top-5 inteiro com o score, o modelo decide | 96% | 96% | 98% | 0 de 10 | 11.686 caracteres |

Quando a nota certa chega ao modelo, ele usa (as duas primeiras colunas batem nas três regras). Nas paráfrases, citar a nota certa foi de 27% na A pra 87% na C. E mesmo vendo o top-5 inteiro, ele não citou nota em nenhuma das 10 perguntas sem resposta, inclusive na que tem o top-1 acima de 0.55. A coluna "correta" do juiz deu 100% em tudo e não separa nada, porque o Sonnet sabe Git e SQL sem precisar do vault.

Só que no modo controlado o modelo lê a nota inteira, e no uso real o `search` mostra um trecho de 200 caracteres e o agente decide se abre o arquivo. O segundo script, `run_agent_eval.py`, roda o dennou de verdade. Cada pergunta vira um `claude -p` com as mesmas ferramentas e permissões do `bot.py`, numa cópia do projeto em `~/.cache/dennou-agent-eval` com o vault do eval. As duas regras têm o mesmo `CLAUDE.md` e só mudam o parágrafo do corte. Rodei as 35 perguntas em que o corte pesa (paráfrase, inglês e sem resposta). A nota citada é achada no código, procurando título, nome do arquivo ou id na resposta, e só conta nota que o agente viu na busca ou abriu.

| regra | buscou no vault | citou nota certa | nota certa só abaixo de 0.55: citou | falso positivo | fiel | notas abertas por pergunta | tempo médio |
|---|---|---|---|---|---|---|---|
| corte: ignora notas abaixo de 0.55 | 97% | 76% | 0 de 4 | 0 de 10 | 94% | 0,1 | 14 s |
| pista: o score é pista, o agente abre a nota antes de usar | 100% | 96% | 5 de 5 | 0 de 10 | 94% | 0,8 | 14 s |

O agente não manda a pergunta crua pro `search`. Ele reescreve, às vezes junta termo em inglês, e isso muda o score, por isso o número de perguntas com a nota certa só abaixo do corte varia de uma regra pra outra (4 e 5). Com a regra nova ele recuperou todas e não citou nada nas perguntas sem resposta, sem gastar tempo a mais. Cada regra teve duas respostas infiéis. Na "pista", ele abriu a nota e mesmo assim pôs na conta dela coisas que eram conhecimento próprio. Na "corte", ele citou a nota só pelo trecho, sem abrir, e errou o que ela diz.

Adotei a regra "pista" no `CLAUDE.md`. Numa rodada anterior, com o `CLAUDE.md` de antes, o agente pulou a busca em três paráfrases, tratando "voltei o projeto pra uma versão antiga" como pergunta sobre o diretório onde ele roda. Por isso o `CLAUDE.md` agora manda buscar sempre, e esses números já são com essa instrução.

Os limites são os de sempre, e mais alguns. Foi uma rodada por pergunta, a coluna do corte se apoia em 4 ou 5 casos, e o juiz é da mesma família do modelo que responde. O modo agente custou uns US$ 4,70 em preço de lista, e o controlado uns US$ 8,50. Pra quem for reproduzir, rodando de dentro do `/tmp`, o Claude Code não carrega o `CLAUDE.md` do diretório, então a cópia do projeto fica em `~/.cache`. As transcrições (`eval/results/agent/runs.jsonl`) ficam fora do git, porque trazem caminhos locais.

### Gate do CI

O `make eval-quick` indexa as 80 notas com a config de produção (`minilm-chunk-title`), roda 10 perguntas fixas (`QUICK_QUERIES` em `run_eval.py`, nenhuma de cauda) e falha se o Recall@5 ficar abaixo de `EVAL_QUICK_MIN_RECALL`, que é 0.8. Com a nota inteira ele dava 1.0. Com chunks dá 0.9, porque a q026 (uma paráfrase sobre `git revert`) cai pra fora do top-5, e ela erra também no eval completo. Mantive o mínimo em 0.8, então o gate aguenta mais um erro antes de quebrar. Leva uns 20 segundos em CPU depois que o MiniLM está no cache.
