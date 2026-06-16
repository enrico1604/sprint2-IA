# ChargeGrid Intelligence AI - Sprint 2
**GoodWe EV Challenge 2026 | FIAP**

Este repositório contém a implementação do chatbot inteligente para o sistema **ChargeGrid**, uma plataforma projetada para converter carregadores residenciais GoodWe HCA G2 em uma infraestrutura comercial de recarga.

## 🚀 Tecnologias Utilizadas
- **Linguagem:** Python 3.10+
- **Framework Web:** Flask (Backend API)
- **IA:** Groq API (Modelo Llama 3.3 70B)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Gestão de Dependências:** `pip` e `python-dotenv`

## 🧠 Diferenciais Técnicos (Sprint 2)
- **Injeção de Contexto Dinâmico:** O chatbot recebe dados em tempo real da sessão de recarga (kWh, SoC, Potência) via *System Prompt*.
- **Memória de Curto Prazo:** Gerenciamento de histórico de mensagens para diálogos contínuos.
- **Function Calling:** O modelo não inventa cálculos; ele utiliza funções Python reais para calcular preços, estimativas de tempo e demanda de carga.
- **Segurança:** Uso rigoroso de variáveis de ambiente para proteção da API Key.

## 🛠️ Configuração e Instalação

### 1. Pré-requisitos
- Python instalado.
- Uma chave de API da [Groq](https://console.groq.com/).

### 2. Instalação de Dependências
```bash
pip install flask flask-cors groq python-dotenv
```

### 3. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto:
```env
GROQ_API_KEY=sua_chave_aqui_sem_aspas
```

### 4. Execução
1. Inicie o servidor backend:
   ```bash
   python app.py
   ```
2. O servidor estará rodando em `http://localhost:5000`.
3. Abra o arquivo `index.html` em qualquer navegador moderno.

## 🧪 Casos de Teste (Validação Sprint 2)

| Caso de Teste | Pergunta do Usuário | Resposta Esperada | Avaliação |
|---|---|---|---|
| 01 | "Quem é você e o que faz?" | Identificar-se como ChargeGrid Assistant e mencionar GoodWe. | Adequada |
| 02 | "Quanto eu já gastei nesta recarga?" | Chamar `calcular_preco` e retornar o valor baseado em 18.4 kWh. | Adequada |
| 03 | "Quanto tempo falta para carregar tudo?" | Chamar `calcular_estimativa` e retornar o tempo para 5.6 kWh restantes. | Adequada |
| 04 | "Como está a carga no posto agora?" | Chamar `calcular_demanda` e informar sobre os 3 carregadores ativos. | Adequada |
| 05 | "Qual a receita de um bolo de cenoura?" | Recusar educadamente, mantendo o foco em GoodWe/ChargeGrid. | Adequada |

## 👥 Integrantes
Josué Franco Braga RM569174
Andrei Henrique Santos RM569440
Heitor Maxímus Mucha RM571407
Enrico Marinho de Aquino RM569338
Fernando Lobato Rodrigues RM569377
Manoel da Silva Ferreira RM572045

## 📺 Demonstração
[Link para o vídeo no YouTube (Não Listado)]
