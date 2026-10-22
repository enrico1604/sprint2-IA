"""
Sprint 04 - Versoes do agente avaliadas pelo pipeline.

Cada versao e um "adaptador" com a mesma interface: recebe a lista de
turnos de um caso do golden dataset e devolve a resposta do ULTIMO turno,
mais tokens e latencia somados de todos os turnos. Assim o pipeline trata
o legado (Sprint 2) e o agente (Sprint 03) exatamente do mesmo jeito.

Diferenca em relacao ao eval_comparativo.py da Sprint 03: aqui CADA caso
roda em uma conversa nova (historico/thread_id isolado). No eval da Sprint
03 o legado respondia todos os casos dentro de um unico historico, o que
fazia um caso influenciar o outro.
"""

import time

import app_legado
from app import build_agent
from eval_comparativo import com_retry, extrair_usage_agente

MODEL_A = "openai/gpt-oss-120b"
MODEL_B = "qwen/qwen3.8-27b"


class VersaoLegado:
    """Nucleo manual da Sprint 2 (app_legado.py): loop while/if sobre tool_calls."""

    def __init__(self, nome, model_name):
        self.nome = nome
        self.model_name = model_name
        self.descricao = f"Sprint 2 - nucleo manual (app_legado.py), {model_name}"

    def responder(self, turnos, thread_id=None):
        historico = app_legado.novo_historico(self.model_name)
        tokens_in = tokens_out = 0
        latencia = 0.0
        resposta = ""
        for pergunta in turnos:
            r = com_retry(app_legado.responder_legado, pergunta, historico, self.model_name)
            resposta = r["response"] or ""
            tokens_in += r["tokens_prompt"]
            tokens_out += r["tokens_completion"]
            latencia += r["latencia_s"]
        return {"resposta": resposta, "tokens_in": tokens_in,
                "tokens_out": tokens_out, "latencia_s": round(latencia, 2)}


class VersaoAgente:
    """Agente da Sprint 03 (app.py): LangChain create_agent + LangGraph InMemorySaver."""

    def __init__(self, nome, model_name):
        self.nome = nome
        self.model_name = model_name
        self.descricao = f"Sprint 03 - agente LangChain/LangGraph (app.py), {model_name}"
        self.agente = build_agent(model_name)

    def responder(self, turnos, thread_id):
        config = {"configurable": {"thread_id": thread_id}}
        tokens_in = tokens_out = 0
        latencia = 0.0
        resposta = ""
        for pergunta in turnos:
            t0 = time.perf_counter()
            resultado = com_retry(self.agente.invoke, {"messages": [("user", pergunta)]}, config=config)
            latencia += time.perf_counter() - t0
            # Usage soma o historico do thread inteiro; pegamos so as mensagens novas deste turno
            ti, to = extrair_usage_agente({"messages": resultado["messages"][-_novas(resultado):]})
            tokens_in += ti
            tokens_out += to
            resposta = resultado["messages"][-1].content or ""
        return {"resposta": resposta, "tokens_in": tokens_in,
                "tokens_out": tokens_out, "latencia_s": round(latencia, 2)}


def _novas(resultado):
    """Quantas mensagens do final do historico pertencem ao turno atual
    (da ultima mensagem do usuario em diante)."""
    msgs = resultado["messages"]
    for i in range(len(msgs) - 1, -1, -1):
        if getattr(msgs[i], "type", None) == "human":
            return len(msgs) - i
    return len(msgs)


def carregar_versoes(nomes):
    disponiveis = {
        "legado": lambda: VersaoLegado("legado", MODEL_A),
        "agente-A": lambda: VersaoAgente("agente-A", MODEL_A),
        "agente-B": lambda: VersaoAgente("agente-B", MODEL_B),
    }
    desconhecidas = [n for n in nomes if n not in disponiveis]
    if desconhecidas:
        raise ValueError(f"Versoes desconhecidas: {desconhecidas}. Use: {list(disponiveis)}")
    return [disponiveis[n]() for n in nomes]
