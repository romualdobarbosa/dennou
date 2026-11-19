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

As notas longas existem pra expor um limite conhecido. O modelo de embedding atual trunca a entrada em 128 tokens, então tudo que vem depois disso some do vetor. Em cada nota longa, uma informação específica aparece só no trecho final, sempre depois de umas 400 palavras. Tipo o nível de isolamento padrão do MySQL, no fim da nota de transações, ou o `loginctl enable-linger`, no fim da nota de systemd. As 12 perguntas listadas em `tail_answer_queries` só têm resposta nesses trechos.

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
