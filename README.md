# 🚀 SQL to Python Modernizer

Um pipeline híbrido e resiliente baseado em Inteligência Artificial (LLMs) para modernização de código legado de banco de dados (PL/pgSQL) para **Python 3.14** e **SQLAlchemy 2.0**.

Desenvolvido como prova de conceito (MVP) para modernização de arquiteturas empresariais, o projeto foca na conversão de lógicas complexas de banco de dados (cursores, transações, bloqueios pessimistas) para uma camada de aplicação escalável e testável.

---

## 🏗 Arquitetura do Sistema (Pipeline Híbrido)

A solução não confia cegamente no LLM. Ela foi desenhada utilizando **LangGraph** para criar um fluxo de trabalho orquestrado (DAG) que implementa validação em múltiplas etapas, garantindo resiliência e integridade do código gerado.

### O Fluxo (DAG)
1. **Parsing (sqlglot):** Realiza a análise sintática estrita do SQL de entrada.
2. **Análise Semântica (Regex/Heurísticas):** Varre o código em busca de "Risk Points" de concorrência e dependências (ex: `FOR UPDATE`, `PRAGMA AUTONOMOUS_TRANSACTION`, cursores).
3. **Geração (Gemini 1.5 Flash):** Recebe o código, os metadados semânticos e um *System Prompt* estrito para converter a lógica para SQLAlchemy 2.0. 
    * 🛡️ **Circuit Breaker (Fail-Fast):** Se a etapa de *Parsing* falhar gravemente em um *payload* malformado e não houver contexto semântico, o pipeline aborta a execução antes de invocar o LLM, poupando custos de rede e limite de quotas (Rate Limit) na nuvem.
4. **Validação (AST):** Analisa a Árvore Sintática Abstrata (`ast.parse`) do código Python gerado. Se o LLM alucinar sintaxe inválida, o erro é capturado e devolvido de forma controlada.

Toda execução (sucesso ou falha) é assincronamente registrada no banco de dados (PostgreSQL) para auditoria.

---

## 🛠 Stack Tecnológica

* **Orquestração de IA:** LangGraph, LangChain, Google Gemini API
* **Backend:** FastAPI (alta performance, validação nativa com Pydantic v2)
* **Banco de Dados & ORM:** PostgreSQL 15, SQLAlchemy 2.0
* **Qualidade e Testes:** Pytest, HTTPX (Testes E2E)
* **Infraestrutura:** Docker, Docker Compose

---

## ⚖️ Trade-offs e Decisões de Design (Visão de Arquitetura)

1. **Testes E2E vs. Unitários (Mock):** 
   Num contexto de pipeline de IA, criar *mocks* da resposta do LLM testaria apenas o framework em si. Priorizou-se o teste E2E com `TestClient` para garantir que a API FastAPI absorve graciosamente falhas externas (ex: erro de Parsing, API do Google indisponível [HTTP 503/429]) sem derrubar o serviço.
   
2. **Delegação Transacional:** 
   As funções Python geradas para substituir as *Procedures* não invocam `session.commit()` internamente. Elas recebem a `Session` injetada e utilizam `session.flush()`, delegando o controle transacional para a camada chamadora (API/Controller). Isso evita problemas de *connection leak* e locks abertos.

3. **Resiliência a Quotas de IA:** 
   O sistema foi testado contra exaustão de quota da API do Google (`RESOURCE_EXHAUSTED`). Em vez de gerar um `HTTP 500`, a API mantém-se responsiva, grava a falha da dependência externa no histórico do banco e retorna o detalhe no `report` do JSON.

---

## 💡 Tratamento de Casos Complexos (Casos de Uso Reais)

O LLM foi instruído e testado contra as armadilhas clássicas do PL/pgSQL (referência aos Anexos D e E do desafio):

* **Prevenção de Deadlock e Double Spending (FOR UPDATE):**
  Ao modernizar a lógica bancária, o bloqueio transacional pessimista foi traduzido para `.with_for_update()`. Mais ainda, a IA foi orientada a carregar os registros utilizando `.order_by(Conta.id)`, o que previne *Deadlocks* mútuos em transferências concorrentes simultâneas (A -> B e B -> A).
* **Precisão Financeira:**
  Tipos `NUMERIC(18,2)` são estritamente convertidos para `from decimal import Decimal` no Python, prevenindo anomalias de arredondamento inerentes ao tipo `float`.
* **Fim dos Cursores (N+1 Query):**
  Loops de banco baseados em cursores (`FETCH NEXT`) são traduzidos usando a funcionalidade `.yield_per(1000)` do SQLAlchemy, limitando o consumo de memória (*OOM - Out of Memory*) e deslocando a carga de processamento do SGBD para a aplicação.

---

## 🚀 Como Executar (Docker)

A aplicação (API e Banco de Dados) está 100% conteinerizada para garantir a melhor experiência de desenvolvimento.

### 1. Configuração do Ambiente
Crie um ficheiro `.env` na raiz do projeto contendo a sua chave da API do Google Gemini:
```env
GEMINI_API_KEY=AIzaSy_sua_chave_valida_aqui
```

### 2. Iniciar a Infraestrutura
Na raiz do projeto, execute:
```bash
docker compose up --build -d
```
O *healthcheck* do Docker garantirá que a API Python apenas iniciará depois de o PostgreSQL estar pronto.

### 3. Acessar a API
A documentação interativa (Swagger UI) ficará disponível imediatamente em:
**🔗 http://localhost:8000/docs**

Para testar diretamente via terminal:
```bash
curl -X 'GET' 'http://localhost:8000/test-db' -H 'accept: application/json'
```

---

## 🧪 Executando os Testes Automatizados

Caso deseje rodar a suíte de testes de integração na sua máquina localmente (fora do Docker):

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Execute o Pytest
pytest -v
```

---
*Desenvolvido por Ranon Emerick Campos como prova de conceito em modernização e arquitetura de software.*
