import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv

# ============================================================
#  CONFIGURAÇÃO INICIAL E SEGURANÇA
# ============================================================

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Recupera a chave de API de forma segura
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("ERRO: A variável de ambiente GROQ_API_KEY não foi configurada no arquivo .env")

client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

app = Flask(__name__)
CORS(app)

# ============================================================
#  DADOS DINÂMICOS DA SESSÃO (Simulação de Contexto Real)
# ============================================================

DADOS_SESSAO = {
    "sessao_ativa": {
        "kwh_consumido": 18.4,
        "kwh_restante": 5.6,
        "potencia_atual_kw": 22.0,
        "tempo_decorrido_min": 50,
        "soc_percentual": 76
    },
    "eletroposto": {
        "nome": "Eletroposto Osasco - FIAP Hub",
        "carregadores_ativos": 3,
        "potencia_total_disponivel_kw": 88.0,
        "conectores_livres": 1,
        "modelo_carregador": "GoodWe HCA G2 (Série Residencial Comercializada)"
    },
    "tarifa_vigente_kwh": 1.20
}

# ============================================================
#  SYSTEM PROMPT - CONTEXTO GOODWE SPRINT 2
# ============================================================

def formatar_dados_dinamicos(dados: dict) -> str:
    s = dados["sessao_ativa"]
    e = dados["eletroposto"]
    t = dados["tarifa_vigente_kwh"]
    return f"""
DADOS DA SESSÃO ATUAL:
- Eletroposto: {e["nome"]}
- Equipamento: {e["modelo_carregador"]}
- Energia consumida: {s["kwh_consumido"]} kWh
- Energia restante estimada: {s["kwh_restante"]} kWh
- Potência de entrega atual: {s["potencia_atual_kw"]} kW
- Tempo de recarga decorrido: {s["tempo_decorrido_min"]} minutos
- Estado de Carga (SoC): {s["soc_percentual"]}%

STATUS DA INFRAESTRUTURA:
- Carregadores em uso: {e["carregadores_ativos"]}
- Potência total do barramento: {e["potencia_total_disponivel_kw"]} kW
- Vagas livres: {e["conectores_livres"]}

TARIFA COMERCIAL: R$ {t}/kWh
"""

SYSTEM_PROMPT = """
Você é o ChargeGrid Assistant, a IA oficial do sistema ChargeGrid AI, desenvolvido para o GoodWe EV Challenge 2026.

SUA MISSÃO:
Transformar carregadores residenciais GoodWe HCA G2 em uma rede de recarga comercial eficiente. Você atende motoristas e operadores.

DIRETRIZES DE COMPORTAMENTO:
1. Responda sempre em Português Brasileiro.
2. Seja profissional, técnico mas acessível.
3. Use o CONTEXTO DINÂMICO fornecido abaixo para responder perguntas sobre a recarga atual.
4. Se o usuário perguntar algo fora do escopo (ex: receitas, política), informe educadamente que seu foco é mobilidade elétrica e a plataforma ChargeGrid.
5. Para cálculos de preço, tempo ou demanda, utilize as FERRAMENTAS disponíveis. Nunca invente valores matemáticos.

CONHECIMENTO ESPECÍFICO:
- GoodWe HCA G2: Suporta carregamento AC, integração com solar, e protocolo OCPP para gestão comercial.
- ChargeGrid: Nossa camada de software que adiciona tarifação e gestão de carga a esses equipamentos.

---
CONTEXTO DINÂMICO DA SESSÃO:
{dados_dinamicos}
---
"""

# ============================================================
#  FERRAMENTAS (FUNCTION CALLING - DIFERENCIAL TÉCNICO)
# ============================================================

def calcular_preco(kwh_consumido: float, tarifa: float) -> dict:
    custo = round(float(kwh_consumido) * float(tarifa), 2)
    return {"resultado": f"O custo atual da sessão é de R$ {custo:.2f}."}

def calcular_demanda(carregadores_ativos: int, potencia_total: float) -> dict:
    potencia_media = round(float(potencia_total) / int(carregadores_ativos), 2)
    return {"resultado": f"Atualmente temos {carregadores_ativos} carregadores dividindo {potencia_total} kW, resultando em uma média de {potencia_media} kW por veículo."}

def calcular_estimativa(kwh_restante: float, potencia_disponivel: float) -> dict:
    minutos = round((float(kwh_restante) / float(potencia_disponivel)) * 60)
    return {"resultado": f"Estimativa de {minutos} minutos para completar a carga."}

FUNCOES_DISPONIVEIS = {
    "calcular_preco": calcular_preco,
    "calcular_demanda": calcular_demanda,
    "calcular_estimativa": calcular_estimativa,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calcular_preco",
            "description": "Calcula o custo financeiro da recarga com base no consumo e tarifa.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kwh_consumido": {"type": "number"},
                    "tarifa": {"type": "number"}
                },
                "required": ["kwh_consumido", "tarifa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_demanda",
            "description": "Analisa a distribuição de carga no eletroposto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "carregadores_ativos": {"type": "integer"},
                    "potencia_total": {"type": "number"}
                },
                "required": ["carregadores_ativos", "potencia_total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_estimativa",
            "description": "Calcula o tempo restante para carga total.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kwh_restante": {"type": "number"},
                    "potencia_disponivel": {"type": "number"}
                },
                "required": ["kwh_restante", "potencia_disponivel"]
            }
        }
    }
]

# ============================================================
#  GERENCIAMENTO DE MEMÓRIA (HISTÓRICO)
# ============================================================

# Em um sistema real, usaríamos sessões de usuário ou banco de dados.
# Para a Sprint 2, manteremos uma lista em memória.
historico_conversa = []

def resetar_historico():
    global historico_conversa
    dados_texto = formatar_dados_dinamicos(DADOS_SESSAO)
    historico_conversa = [{"role": "system", "content": SYSTEM_PROMPT.format(dados_dinamicos=dados_texto)}]

# Inicializa o histórico na primeira execução
resetar_historico()

# ============================================================
#  ROTAS DA API
# ============================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(DADOS_SESSAO)

@app.route('/api/chat', methods=['POST'])
def chat():
    global historico_conversa
    data = request.json
    mensagem_usuario = data.get("message")
    
    if not mensagem_usuario:
        return jsonify({"error": "Mensagem vazia"}), 400

    # Adiciona mensagem do usuário ao histórico (Memória de Contexto)
    historico_conversa.append({"role": "user", "content": mensagem_usuario})
    
    try:
        # Chamada ao modelo com suporte a ferramentas (Diferencial Sprint 2)
        response = client.chat.completions.create(
            model=MODEL,
            messages=historico_conversa,
            tools=TOOLS,
            tool_choice="auto"
        )
        
        mensagem = response.choices[0].message
        
        # Se o modelo decidir usar uma ferramenta
        if mensagem.tool_calls:
            historico_conversa.append(mensagem)
            for tool_call in mensagem.tool_calls:
                func_name = tool_call.function.name
                func = FUNCOES_DISPONIVEIS.get(func_name)
                args = json.loads(tool_call.function.arguments)
                
                # Executa a lógica Python
                resultado = func(**args)
                
                # Adiciona o resultado da ferramenta ao histórico
                historico_conversa.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(resultado)
                })
            
            # Gera a resposta final baseada nos dados calculados
            response_final = client.chat.completions.create(
                model=MODEL,
                messages=historico_conversa
            )
            final_content = response_final.choices[0].message.content
            historico_conversa.append({"role": "assistant", "content": final_content})
            return jsonify({"response": final_content})
        
        # Resposta direta
        historico_conversa.append({"role": "assistant", "content": mensagem.content})
        return jsonify({"response": mensagem.content})
        
    except Exception as e:
        print(f"Erro na API Groq: {e}")
        return jsonify({"response": "Desculpe, tive um problema técnico para processar sua mensagem. Verifique sua conexão e chave de API."}), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    resetar_historico()
    return jsonify({"status": "Histórico resetado"})

if __name__ == '__main__':
    # Rodando na porta 5000 para integração com o frontend
    app.run(port=5000, debug=True)
