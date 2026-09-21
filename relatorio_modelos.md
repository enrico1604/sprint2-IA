# Relatório de uso de modelos e parâmetros (Bloco B)

## Modelos comparados

Ambos servidos via Groq API (mesma chave, sem custo/setup adicional),
usando o mesmo agente (LangChain/LangGraph) e o mesmo eval set — a única
variável isolada é o modelo:

- **Modelo A:** `openai/gpt-oss-120b` — modelo aberto da OpenAI hospedado
  na Groq. Usado também como baseline do legado (ver nota abaixo), o que
  isola o efeito da migração de framework no Bloco D.
- **Modelo B:** `qwen/qwen3.8-27b` — modelo de família/arquitetura
  diferente do A, listado como disponível na conta Groq usada pelo grupo
  (bom contraste de tamanho e proveniência para a comparação).

> **Nota sobre a escolha:** o modelo original da Sprint 2
> (`llama-3.3-70b-versatile`) saiu de linha na Groq entre a Sprint 2 e a
> Sprint 03 (`groq.NotFoundError: model_not_found` ao rodar o eval) — por
> isso o legado também foi reexecutado com o Modelo A, em vez do modelo
> original. Ver "Problemas encontrados e soluções" no relatório de
> evolução.

## Parametrização (idêntica para os dois modelos, para comparação justa)

| Parâmetro | Valor | Justificativa |
|---|---|---|
| `temperature` | 0.3 | Baixa variância nas respostas — importante para cálculos consistentes e para respostas de guardrail previsíveis entre execuções. |
| `top_p` | 0.9 | Mantém alguma diversidade lexical sem abrir espaço para respostas erráticas, combinado com a temperature baixa. |
| `max_tokens` | 1024 | O assistente responde de forma curta/direta (dashboard de atendimento); limite generoso o suficiente para não cortar respostas, sem permitir divagação longa. |

## Metodologia

O mesmo eval set (5 casos de acurácia + 1 caso de memória em 3 turnos + 6
casos de segurança — ver `eval_comparativo.py` e
`docs/casos_teste_seguranca.md`) foi executado com os dois modelos, sob o
mesmo agente e a mesma parametrização. Métricas coletadas por caso:
resposta obtida, tokens (entrada/saída) e latência (segundos).

## Resultados

_(preenchido após rodar `eval_comparativo.py` — tabela com nota de
qualidade 0-10 por caso, tokens médios por turno, latência média, e
resultado dos 6 casos de segurança por modelo)_

| Métrica | Modelo A (llama-3.3-70b) | Modelo B (gpt-oss-120b) |
|---|---|---|
| Nota média de acurácia (0-10) | TODO | TODO |
| Tokens médios/turno | TODO | TODO |
| Latência média (s) | TODO | TODO |
| Casos de segurança resistidos (de 6) | TODO | TODO |

## Seleção final

_(TODO: justificar, com base na tabela acima, qual modelo foi escolhido
como padrão em produção — `MODEL_NAME` em `app.py` — e por quê.)_
