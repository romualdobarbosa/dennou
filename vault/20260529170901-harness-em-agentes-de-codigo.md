---
id: 20260529170901
title: "O harness em agentes de código (Codex vs Claude Code)"
type: concept
tags: [harness, agentes-llm, claude-code, codex, contexto, engenharia-de-software]
area: ciencia-da-computacao
created: 29/05/26
source: agent
related: []
---

## Definição
**Harness** é a camada de orquestração que envolve o LLM — o "sistema operacional" do agente. O modelo puro só prevê os próximos tokens; o harness decide *o que* entra no contexto, *quando*, em que ordem, com quais ferramentas, e o que fazer com a saída. Boa parte da diferença de comportamento entre agentes (ex: Codex vs Claude Code) vem do harness, não só do modelo.

## Como funciona
O contexto do modelo é finito; o harness gerencia esse recurso:
1. **Curadoria do contexto** — busca, recorta e injeta só o relevante (RAG, grep, leitura sob demanda), em vez de despejar o repositório inteiro.
2. **Loop agêntico** — orquestra o ciclo *pensar → chamar ferramenta → observar → repetir*.
3. **Compactação / memória** — resume e re-injeta histórico quando o contexto enche, mantendo continuidade em tarefas longas.
4. **Ferramentas** — define o conjunto de tools (editar, bash, buscar) e como os resultados voltam formatados.
5. **System prompt e instruções** — regras de comportamento, formatação e permissões.

## Codex vs Claude Code
A diferença prática não é só "qual modelo é mais esperto", e sim como cada harness usa o mesmo "motor":
- **Codex (OpenAI):** modelos GPT/codificação; historicamente mais fechado e focado em sessão de codificação.
- **Claude Code (Anthropic):** modelos Claude; harness muito extensível — `CLAUDE.md` (memória de projeto), hooks, skills, subagentes, MCP e settings permitem que o usuário *programe o próprio harness*. Ênfase em curadoria agressiva de contexto e controle do usuário.

> Ressalva: ambos evoluem rápido e nem todos os detalhes internos são públicos.

## Analogia
O modelo é o motor; o harness é o resto do carro (transmissão, direção, painel). Dois carros com motores parecidos dirigem de formas completamente diferentes dependendo do chassi. Muito do que se chama de "esse agente é melhor" é, na verdade, "esse harness usa melhor o mesmo motor".

## Links
