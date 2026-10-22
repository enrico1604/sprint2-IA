"""
Sprint 04 - Modelo juiz (LLM as a judge) para o DeepEval.

O DeepEval usa a OpenAI como juiz por padrao. Como o grupo so tem chave da
Groq, este modulo implementa um DeepEvalBaseLLM sobre o ChatGroq, com
temperature 0 (juiz deterministico) e o mesmo retry de rate limit usado no
eval da Sprint 03.

Escolha do juiz: por padrao usamos qwen/qwen3.8-27b, de familia diferente
do openai/gpt-oss-120b usado no legado e no agente A, para reduzir o vies de
um modelo avaliar as proprias respostas (self-preference). O efeito colateral
e que o juiz e o mesmo modelo do agente B - isso esta discutido nas
limitacoes do relatorio. Pode ser trocado com a variavel JUIZ_MODEL ou com
--juiz na linha de comando.
"""

import os
import re

from deepeval.models import DeepEvalBaseLLM
from langchain_groq import ChatGroq

from eval_comparativo import com_retry

JUIZ_MODEL_PADRAO = os.environ.get("JUIZ_MODEL", "qwen/qwen3.8-27b")

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class JuizGroq(DeepEvalBaseLLM):
    def __init__(self, model_name=JUIZ_MODEL_PADRAO):
        self.model_name = model_name
        # max_tokens abaixo do teto de 1000 tokens/min de saida do qwen na conta do grupo
        self.llm = ChatGroq(
            model=model_name,
            api_key=os.environ.get("GROQ_API_KEY"),
            temperature=0,
            max_tokens=800,
        )
        # Sem JSON mode da Groq: ele nao combina com o raciocinio "raw" de
        # modelos como o qwen. O DeepEval extrai o JSON do texto, e o bloco
        # <think> e removido antes em generate().

    def load_model(self):
        return self.llm

    def generate(self, prompt, schema=None, **kwargs):
        resposta = com_retry(self.llm.invoke, prompt)
        return _THINK.sub("", resposta.content).strip()

    async def a_generate(self, prompt, schema=None, **kwargs):
        return self.generate(prompt, schema=schema, **kwargs)

    def get_model_name(self):
        return self.model_name
