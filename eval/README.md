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
make eval         # as 12 configs e o experimento do related, grava em eval/results/
make eval-quick   # gate do CI, 10 perguntas fixas com a config de produção
```

O `make eval` roda tudo em CPU (dá pra trocar com `uv run python -m eval.run_eval --device cuda`) e baixa o e5-small e o bge-m3 na primeira vez, uns 2,5 GB no cache do Hugging Face. Cada config indexa `eval/vault` num Chroma temporário, com distância cosseno igual à produção, e nunca encosta no vault real nem no `chroma_db/`. Os resultados ficam em `eval/results/<config>.json`, com as métricas, a curva de threshold, o top-5 de cada pergunta e os metadados da rodada (modelo, `max_seq_length`, chunking, commit, CPU, versão do torch). A tabela comparativa sai em `eval/results/summary.md`.

As configs cruzam três modelos (o `paraphrase-multilingual-MiniLM-L12-v2` de produção, o `intfloat/multilingual-e5-small` com os prefixos `query: ` e `passage: ` que ele exige, e o `BAAI/bge-m3`), nota inteira contra chunks, e texto com e sem o título. A config `minilm-chunk-title` é a de produção (antes era `minilm-whole-title`, uma nota inteira por vetor). O harness não tem cópia da lógica de produção. Ele chama as funções do `embed.py` pra ler a nota, quebrar em chunks (`note_chunks`), gravar no Chroma (`index_note`), juntar os chunks por nota (`best_chunk_per_note`) e calcular o score, e o corte vem do mesmo `SCORE_THRESHOLD`. Conferi que o top-5 dela bate com o `embed.py search` nas 60 perguntas.

### Chunks

O chunking é o do `embed.py`, o mesmo da produção. Os chunks juntam parágrafos seguidos (sem partir bloco de código) até 256 tokens, ou até o `max_seq_length` do modelo se ele for menor, contando prefixo, título e tokens especiais. No MiniLM isso dá 128, então nenhum chunk é cortado. Parágrafo que sozinho não cabe vira janelas de palavras com 20% de sobreposição. O score da nota é o maior score entre os chunks dela, e cada nota aparece uma vez só no ranking.

### Métricas

Só as 50 perguntas com resposta entram em recall, MRR e nDCG. As 10 `no_answer` servem pro threshold.

- Recall@k vale 1 se pelo menos uma nota de grau 2 aparece no top-k. Quando a pergunta tem duas notas de grau 2 (WHERE e HAVING, por exemplo), achar uma já conta.
- MRR é a média de 1/posição da primeira nota de grau 2 no top-10.
- nDCG@5 usa ganho igual ao grau (2 ou 1), desconto log2(posição + 1), normalizado pelo ranking ideal das notas rotuladas.
- Latência é o p50 e o p95 de encode da pergunta mais a consulta no Chroma, depois de uma chamada de aquecimento. Indexação é o tempo total de encode e upsert das 80 notas, sem contar o carregamento do modelo.

Também separo o Recall@5 das 12 perguntas de cauda, as do `tail_answer_queries`.

### Threshold

O agente só usa nota com score ≥ 0.55 (`DENNOU_SCORE_THRESHOLD`, que antes era 0.4). Pra cada config calculo uma curva de 0.0 a 1.0, de 0.05 em 0.05. Num eixo fica o falso positivo, que é a fração das perguntas `no_answer` cujo top-1 passa do threshold (o agente usaria uma nota que não responde nada). No outro fica o Recall@5 das perguntas com resposta contando só as notas acima do threshold. O threshold sugerido é o de maior recall com falso positivo de no máximo 10% (no empate, o menor falso positivo e depois o threshold mais alto). Com só 10 perguntas sem resposta, cada uma vale 10 pontos de falso positivo, então trate esse número como indicação e não como valor exato. O score muda de escala entre modelos (no e5 tudo fica acima de 0.7), por isso o threshold não passa de um modelo pro outro.

### Expansão pelo related

Na melhor config por nDCG@5, as notas listadas no `related` das top-3 entram com score max(score próprio, λ × score da nota de origem), e a lista é reordenada. Com λ = 1 a relacionada fica logo atrás da origem. Rodo λ = 0.8, 0.9 e 1.0.

### Gate do CI

O `make eval-quick` indexa as 80 notas com a config de produção (`minilm-chunk-title`), roda 10 perguntas fixas (`QUICK_QUERIES` em `run_eval.py`, nenhuma de cauda) e falha se o Recall@5 ficar abaixo de `EVAL_QUICK_MIN_RECALL`, que é 0.8. Com a nota inteira ele dava 1.0. Com chunks dá 0.9, porque a q026 (uma paráfrase sobre `git revert`) cai pra fora do top-5, e ela erra também no eval completo. Mantive o mínimo em 0.8, então o gate aguenta mais um erro antes de quebrar. Leva uns 20 segundos em CPU depois que o MiniLM está no cache.
