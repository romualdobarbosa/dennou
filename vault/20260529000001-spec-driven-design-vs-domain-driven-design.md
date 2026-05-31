---
id: 20260529000001
title: Spec Driven Design vs Domain Driven Design
type: concept
tags:
  - spec-driven-design
  - domain-driven-design
  - ddd
  - sdd
  - arquitetura
  - software-design
area: ciencia-da-computacao
created: 29/05/26
source: agent
related: []
---

## Definição

**Domain Driven Design (DDD):** abordagem criada por Eric Evans (2003) que modela o software em torno do domínio do problema — o negócio real.

**Spec Driven Design (SDD):** abordagem que define contratos, interfaces e comportamentos esperados *antes* do código. A spec é a fonte de verdade.

## Como funciona

### DDD
- **Ubiquitous Language** — linguagem comum entre devs e especialistas do domínio
- **Bounded Contexts** — limites onde um modelo de domínio é válido
- **Entities, Value Objects, Aggregates** — modelagem dos dados do domínio
- **Domain Services, Repositories** — organização da lógica

### SDD
- A spec (ex: OpenAPI, JSON Schema, testes de contrato) define o comportamento esperado
- O código é desenvolvido para satisfazer a spec
- Muito usado em design de APIs

## Analogia

DDD é como entrevistar os especialistas do negócio para descobrir como o mundo funciona e refletir isso no código. SDD é como escrever o manual de instruções antes de construir o produto.

## Comparação

| | DDD | Spec Driven |
|---|---|---|
| **Foco** | Modelagem do domínio de negócio | Definição de contratos e comportamentos |
| **Ponto de partida** | Linguagem e lógica do negócio | Especificação formal (OpenAPI, schema, teste) |
| **Artefato central** | Modelo de domínio | Spec/contrato |
| **Quem lidera** | Especialistas do domínio + devs | Devs + consumidores da interface |
| **Escopo** | Arquitetura e modelagem interna | Interface e comportamento externo |

São complementares: DDD internamente, SDD para interfaces externas.

## Links
