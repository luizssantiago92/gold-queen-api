# Product Requirement Document (PRD) — Back-end Engine

## 1. Identificação do Repositório
* **Nome do Repositório:** `gold-queen-api`
* **Descrição do Repositório:** *"RESTful API for Open Finance data aggregation, automated transaction categorization, and medieval-themed financial AI advisor using FastAPI, PostgreSQL, and Spec-Guardrails."*

---

## 2. Visão Geral do Produto
O **Gold Queen API** é o motor de back-end responsável por conectar bancos via Open Finance (Pluggy Sandbox), unificar e categorizar transações de até 3 contas bancárias ativas (limitadas na regra de negócio para simular o modelo Freemium de mercado), validar a inferência da IA utilizando a biblioteca `spec-guardrails`, gerar análises ativas de educação financeira (*Dicas da Rainha*) e responder a dúvidas do usuário através da persona **Gold Queen** (a Rainha da Era Medieval e Mestre da Moeda) com controle estrito de uso (Rate Limiting por tokens).

---

## 3. Arquitetura e Tech Stack
* **Linguagem:** Python 3.11+
* **Framework:** FastAPI (Assíncrono)
* **Banco de Dados:** PostgreSQL (Instância local via Docker / Supabase no deploy)
* **ORM:** SQLModel (SQLAlchemy + Pydantic v2)
* **Open Finance SDK/Client:** Pluggy Sandbox API
* **Engine de IA:** Google GenAI SDK (`gemini-1.5-flash`)
* **Validação de IA:** `spec-guardrails` (Biblioteca própria de resiliência e validação)
* **Otimização de Custos & Cache:** In-Memory Cache (`functools.lru_cache`) para reutilizar análises e respostas de perguntas idênticas no mesmo dia sem consumir tokens adicionais.
* **Rate Limiting:** Token Bucket (Max 10 interações/dia por usuário para custo $0.00)

---

## 4. Requisitos Funcionais & Endpoints

### RF01 - Gestão de Conexões Bancárias (Open Finance)
* Limitador de plano Free: Máximo de **3 conexões bancárias** por usuário (`POST /v1/connections/connect`).
* Sincronização e consolidação das contas e saldos (`POST /v1/connections/sync`).

### RF02 - Agregação e Categorização de Gastos com Guardrails
* Leitura de extrato do Pluggy Sandbox.
* Envio de transações não categorizadas para a IA (Gemini).
* Aplicação obrigatória da `spec-guardrails` para garantir que `category`, `amount` e `date` venham estritamente no schema correto sem alucinações.
* Retorno de uma flag booleana (`is_guarded: true`) em cada transação para auditoria visual na interface.
* Persistência no PostgreSQL.

### RF03 - Endpoints do Dashboard
* `GET /v1/dashboard/overview`: Retorna saldo total consolidado do tesouro, lista de bancos com seus respectivos saldos e percentual do total, e total de gastos do mês.
* `GET /v1/dashboard/categories`: Retorna a divisão de gastos por categoria no mês atual.
* `GET /v1/dashboard/transactions`: Retorna o feed unificado de transações recentes paginado contendo o status de validação do guardrail.

### RF04 - Dicas da Rainha (Análise Ativa Preditiva)
* `GET /v1/advisor/queen-tips`: Consolida o perfil e os gastos do mês do usuário e gera um diagnóstico financeiro estruturado via IA.
* **Saída Estruturada (JSON):**
  * `critical_expense`: Ponto principal de vazamento de caixa no reino.
  * `management_status`: Avaliação geral de como o dinheiro está sendo gerido.
  * `smart_guidance`: Orientação e educação financeira personalizada para o contexto do usuário.

### RF05 - Chatbot Mestre da Moeda (Consulte a Gold Queen)
* `POST /v1/chat/query`: Recebe a pergunta do usuário.
* **Cache Check:** Verifica se a pergunta exata já foi respondida no dia. Em caso afirmativo, retorna a resposta em cache diretamente.
* **System Instruction da IA (Persona Medieval):** *"Você é a Gold Queen, a Mestre da Moeda e Soberana do Reino. Seu papel é analisar os gastos e dar conselhos financeiros com tom de sabedoria, nobreza e autoridade medieval. Trate o patrimônio como o 'Tesouro do Reino' e oriente o usuário a proteger seu ouro com precisão cirúrgica."*
* **Rate Limiting:** Valida o limite de uso (10 requisições diárias). Se atingir, retorna status `429 Too Many Requests` com mensagem temática para a persona da Rainha.

---

## 5. Modelos Futuros (Roadmap de Cartões & Investimentos)
* **Tabela `Cards`:** `id`, `user_id`, `tier` (`STANDARD` | `PLATINUM`), `art_variant` (1 a 4).
* **Tabela `InvestmentAdvice`:** Recomendações e sugestões de aportes calculados com base no excedente de caixa do usuário.

---

## 6. Requisitos de Aprendizado & Fontes para os Agentes de IA

Para a execução com maestria deste repositório, o agente deve consultar:
1. **Documentação da API da Pluggy:** Estudar a criação de Connect Tokens e o endpoint `/transactions`.
2. **Repositório Spec-Guardrails:** Consultar https://github.com/luizssantiago92/spec-guardrails para entender os decoradores e validadores de schema JSON para LLM.
3. **FastAPI & SQLModel:** Boas práticas de injeção de dependência e rotas assíncronas.

---

## 7. Instruções de Setup Inicial (Bash)

```bash
# Inicializar ambiente
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependências essenciais
pip install fastapi uvicorn sqlmodel psycopg2-binary python-dotenv google-genai requests
pip install git+[https://github.com/luizssantiago92/spec-guardrails.git](https://github.com/luizssantiago92/spec-guardrails.git)