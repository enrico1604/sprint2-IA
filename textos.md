<!--
Textos do relatório final da Sprint 04. O gerar_relatorio.py monta o PDF
juntando estes textos com as tabelas geradas a partir de
eval/resultados/resumo.json. Cada seção começa com "## <chave>".
Formatação aceita: parágrafos, listas com "- " e **negrito**.
Trechos marcados com [PREENCHER] dependem dos resultados do pipeline.
-->

## introducao

Na Sprint 03 o ChargeGrid Assistant foi reconstruído com LangChain/LangGraph e avaliado manualmente: o grupo leu as respostas de 12 casos de teste e classificou cada uma como adequada, "resistiu" ou "vazou". A Sprint 04 substitui essa checagem manual por um **pipeline de avaliação automatizado e reprodutível**, que roda um golden dataset contra cada versão do agente e atribui notas por critério usando **LLM as a judge** (DeepEval) e checagens determinísticas.

## golden_dataset

O golden dataset (eval/golden_dataset.json) foi construído a partir dos casos de teste já existentes, e não do zero. Os 5 casos de acurácia das Sprints 1/2, o caso de memória em 3 turnos e os 6 casos de segurança da Sprint 03 foram mantidos com os mesmos textos, para permitir a comparação com a avaliação manual. A eles somamos casos novos para cobrir lacunas que a avaliação manual não testava:

- **Funcionalidade:** outras consultas à sessão (SoC, tempo decorrido, potência média, custo do restante) e um segundo caso de memória com valor hipotético.
- **Escopo:** perguntas fora do escopo (política, programação) e, no sentido oposto, uma pergunta dentro do escopo (AC x DC) para detectar recusa excessiva.
- **Segurança:** injection indireta (instrução escondida numa mensagem colada), extração ofuscada (base64), tentativa de fraude na medição e modificação elétrica perigosa.
- **Borda:** entrada vazia, pergunta em inglês, linguagem informal, tarifa negativa, potência zero (que provoca divisão por zero nas ferramentas) e informação ausente no contexto (preço do carregador).

Cada caso tem um **gabarito** (resposta esperada escrita pelo grupo) e uma lista de **critérios de aceite**. Os valores numéricos do gabarito foram calculados a partir do contexto fixo da sessão (18,4 kWh consumidos, 5,6 kWh restantes, 22 kW, tarifa de R$ 1,20/kWh etc.). Os casos de segurança e de escopo indicam se a resposta correta é uma recusa.

## pipeline

O pipeline (eval/pipeline.py) tem três etapas retomáveis. Primeiro, cada versão do agente responde a todos os casos, cada caso em uma conversa nova, e o pipeline registra resposta, tokens e latência. Depois, cada resposta é avaliada pelas métricas abaixo. Por fim, os resultados são consolidados em tabelas por versão, por métrica e por categoria, e confrontados com a avaliação manual da Sprint 03.

Escolhemos o **DeepEval** com a métrica **GEval** porque ela permite escrever os critérios de avaliação em linguagem natural (em português, alinhados ao nosso system prompt) e devolve uma nota com justificativa, o que facilita auditar o juiz. O Ragas foi descartado porque suas métricas principais pressupõem um pipeline de RAG com documentos recuperados, que o nosso agente não tem. Como o grupo só possui chave da Groq, implementamos um juiz próprio (eval/juiz.py) sobre o ChatGroq, com temperature 0. Os passos de avaliação de cada métrica são fixos no código, e não gerados pelo juiz a cada execução, para que as notas sejam comparáveis entre versões.

## metricas_nota

A **nota final** de cada versão é a média simples das cinco métricas (todas com o mesmo peso), multiplicada por 10. Cada métrica é a média das notas dos casos em que ela se aplica. Um caso é considerado **aprovado** em uma métrica quando a nota é maior ou igual a 0,5.

## classificacao

[PREENCHER após rodar o pipeline: qual versão ficou em 1º lugar, por quanto, e em quais métricas e categorias a diferença aparece. Citar os números da tabela.]

## comparacao_manual

[PREENCHER após rodar o pipeline: onde o pipeline concorda com a avaliação manual (esperado: SEC-4 e SEC-5 reprovados no legado), onde diverge e por quê. Hipóteses a discutir: o juiz pode ser mais ou menos rigoroso que o grupo; na Sprint 03 o legado respondia todos os casos em um único histórico, aqui cada caso roda isolado; as respostas variam entre execuções mesmo com temperature 0,3.]

## limitacoes

- **Viés do juiz:** o juiz padrão (qwen/qwen3.8-27b) é de família diferente do modelo do legado e do agente A, o que reduz o viés de um modelo favorecer as próprias respostas. Porém ele é o mesmo modelo do agente B, que pode ser favorecido. [PREENCHER se o grupo rodar com um segundo juiz e comparar.]
- **Cobertura do golden dataset:** 32 casos cobrem os fluxos principais, mas não são estatisticamente representativos. Uma diferença de poucos casos entre versões pode ser ruído.
- **Variabilidade:** as respostas dos agentes mudam entre execuções (temperature 0,3), então a nota de uma única execução é uma amostra. Repetir a execução e tirar a média reduziria esse efeito.
- **Custo e latência:** cada execução completa faz cerca de 100 chamadas aos agentes e cerca de 300 chamadas ao juiz. No tier gratuito da Groq isso leva bastante tempo por causa do rate limit, o que limita quantas vezes o pipeline pode ser repetido.
- **Métrica determinística simples:** a checagem de valores procura os números do gabarito na resposta por expressão regular. Ela pode aceitar um número certo citado no contexto errado.

## conclusao

[PREENCHER após rodar o pipeline: evolução do projeto ao longo das sprints. A Sprint 1 definiu problema, persona e 5 casos de teste; a Sprint 2 implementou o chatbot com function calling manual; a Sprint 03 migrou para LangChain/LangGraph com guardrails e avaliou manualmente; a Sprint 04 mede tudo isso de forma automática. Fechar com o que os números mostram sobre o ganho real de cada sprint.]

## equipe

- Josué Franco Braga | RM569174 | [PREENCHER tarefa principal]
- Andrei Henrique Santos | RM569440 | [PREENCHER tarefa principal]
- Heitor Maxímus Mucha | RM571407 | [PREENCHER tarefa principal]
- Enrico Marinho de Aquino | RM569338 | [PREENCHER tarefa principal]
- Fernando Lobato Rodrigues | RM569377 | [PREENCHER tarefa principal]
- Manoel da Silva Ferreira | RM572045 | [PREENCHER tarefa principal]
