# SQL to Python Modernizer

Um pipeline híbrido e resiliente baseado em Inteligência Artificial (LLMs) para modernização de código legado de bases de dados (PL/pgSQL) para Python 3.14 e SQLAlchemy 2.0.

Desenvolvido como prova de conceito (MVP) para modernização de arquiteturas empresariais, o projeto foca na conversão de lógicas complexas de base de dados (cursores, transações, bloqueios pessimistas) para uma camada de aplicação escalável, testável e monitorizada.

---

## 1. Arquitetura do Sistema (Pipeline Híbrido)

A solução mitiga as alucinações inerentes aos Modelos de Linguagem de Grande Escala (LLMs) através de um fluxo de trabalho orquestrado (DAG) com o LangGraph, implementando validação em múltiplas etapas para garantir a resiliência e a integridade do código gerado.

### O Fluxo de Orquestração (DAG)
1. **Parsing (sqlglot):** Análise sintática estrita do SQL de entrada para extração de tokens e validação primária.
2. **Análise Semântica (Heurísticas):** Identificação de "Risk Points" de concorrência e dependências estruturais (ex: FOR UPDATE, PRAGMA AUTONOMOUS_TRANSACTION, manipulação de cursores).
3. **Geração (Gemini 1.5 Flash):** Processamento do código e dos metadados semânticos sob um System Prompt rigoroso para conversão arquitetural para SQLAlchemy 2.0. 
    * **Circuit Breaker (Fail-Fast):** Falhas críticas na etapa de Parsing ou ausência de contexto semântico abortam a execução antes da invocação do LLM, otimizando o consumo de rede e prevenindo exaustão de limites de quota (Rate Limit).
4. **Validação (AST):** Inspeção da Árvore Sintática Abstrata (ast.parse) do código Python resultante. Falhas de compilação por alucinação sintática são capturadas e geridas antes do retorno ao cliente.

Toda a execução do pipeline (sucesso ou falha) é registada assincronamente na base de dados PostgreSQL para efeitos de auditoria.

---

## 2. Stack Tecnológica

* **Orquestração de IA:** LangGraph, LangChain, Google Gemini API
* **Observabilidade e Telemetria:** Langfuse
* **Backend:** FastAPI, Pydantic v2
* **Base de Dados & ORM:** PostgreSQL 15, SQLAlchemy 2.0
* **Qualidade e Testes:** Pytest, HTTPX (Testes de Integração/E2E)
* **Infraestrutura:** Docker, Docker Compose

---

## 3. Observabilidade e Rastreio de IA (Langfuse)

O projeto implementa telemetria avançada no orquestrador LangGraph através da integração com o Langfuse (CallbackHandler). Esta camada arquitetural garante visibilidade total sobre o comportamento do pipeline de IA, providenciando:

* **Rastreamento de Execução (Traces):** Mapeamento do tempo de execução e latência de cada nó do DAG (Parsing, LLM, Validation).
* **Auditoria de Prompts:** Registo integral do input enviado ao modelo e do respetivo output gerado.
* **Controlo de Custos e Uso:** Monitorização do consumo de tokens por requisição.
* **Captura de Exceções Externas:** Registo de indisponibilidades da API provedora do modelo fundacional.

![Trace de Execução do Langfuse](/docs/langfuse.png)
*Exemplo visual do rastreio de execução do orquestrador LangGraph.*

---

## 4. Trade-offs e Decisões de Design

1. **Testes E2E vs. Mocks Unitários:** 
   No contexto de um pipeline de IA, a simulação (mocking) da resposta do LLM testaria apenas as interfaces do framework. Priorizou-se o teste de integração (E2E) com TestClient para validar a capacidade da API FastAPI em absorver falhas externas reais (ex: indisponibilidade HTTP 503/429 da API do Google) sem interrupção do serviço.
   
2. **Delegação Transacional:** 
   O código gerado para substituir as Procedures omite invocações de session.commit() internas. O design exige injeção de dependência da Session e utilização de session.flush(), transferindo o controlo transacional para a camada de serviço/controlador. Esta abordagem previne connection leaks e bloqueios residuais.

3. **Resiliência a Quotas de IA:** 
   O sistema foi arquitetado para suportar cenários de exaustão de quota (RESOURCE_EXHAUSTED). Em vez de propagar um erro de servidor (HTTP 500), a API garante graciosidade, regista a falha da dependência externa no histórico transacional e devolve o detalhe padronizado no payload da resposta.

---

## 5. Tratamento de Casos de Uso Complexos

O pipeline foi validado contra padrões complexos de implementações PL/pgSQL legadas:

* **Prevenção de Deadlock e Duplo Gasto (FOR UPDATE):**
  Lógicas transacionais pessimistas são convertidas para .with_for_update(). Adicionalmente, o LLM assegura a ordenação prévia dos registos (.order_by), prevenindo Deadlocks mútuos em transferências financeiras concorrentes simultâneas (A -> B e B -> A).
* **Precisão Financeira:**
  Colunas e variáveis do tipo numérico exato (ex: NUMERIC(18,2)) são estritamente mapeadas para a classe Decimal do Python nativo, eliminando anomalias de arredondamento intrínsecas à aritmética de vírgula flutuante (float).
* **Erradicação de Cursores (N+1 Query Problem):**
  Iterações baseadas em cursores de base de dados (FETCH NEXT) são reestruturadas mediante a utilização do método iterador .yield_per(1000) do SQLAlchemy. Este padrão mitiga problemas de esgotamento de memória (OOM) na camada de aplicação e minimiza a latência e o bloqueio de CPU no Sistema de Gestão de Bases de Dados.

---

## 6. Procedimentos de Execução (Ambiente Docker)

A infraestrutura (API e Base de Dados) encontra-se totalmente conteinerizada para assegurar a replicabilidade do ambiente.

### 6.1. Configuração de Variáveis de Ambiente
Crie um ficheiro `.env` na diretoria raiz do projeto com as credenciais necessárias:
```env
# Provedor do Modelo Fundacional
GEMINI_API_KEY=sua_chave_do_google_gemini

# Telemetria e Observabilidade (Opcional, porém recomendado)
LANGFUSE_PUBLIC_KEY=sua_chave_publica
LANGFUSE_SECRET_KEY=sua_chave_privada
LANGFUSE_HOST=[https://cloud.langfuse.com](https://cloud.langfuse.com)
```

### 6.2. Inicialização dos Serviços
Na raiz do repositório, execute o processo de build e deploy dos contentores:
```bash
docker compose up --build -d
```
*O sistema implementa healthchecks, garantindo que a aplicação Python apenas aceita requisições após a inicialização e prontidão do PostgreSQL.*

### 6.3. Acesso à Aplicação
A documentação interativa da API (Swagger UI) ficará acessível no seguinte endereço:
**http://localhost:8000/docs**

Para testar a conectividade primária via terminal:
```bash
curl -X 'GET' 'http://localhost:8000/test-db' -H 'accept: application/json'
```

---

## 7. Visão de Futuro e Escalabilidade (Roadmap)

Para preparar a solução para um ambiente de produção de alta escala (processamento em massa de centenas de Procedures legadas simultaneamente), a arquitetura prevê as seguintes evoluções:

* **Processamento Assíncrono com Filas (Queues/Workers):**
  Atualmente a API responde de forma síncrona. Em produção, requisições de modernização longas deverão ser publicadas numa fila (ex: **RabbitMQ** ou **Kafka**) e processadas por Workers (ex: **Celery**), devolvendo ao cliente apenas um `job_id` para consulta posterior (Webhooks ou Polling).
* **Paralelização do LangGraph:**
  Para scripts gigantes contendo múltiplas Procedures num só ficheiro, o grafo pode ser evoluído para utilizar a funcionalidade `.map()` do LangGraph, dividindo o código em chunks e enviando requisições paralelas para a API do Gemini, reduzindo o tempo total de processamento.
* **Camada de Cache (Redis):**
  Implementação de cache semântico (ex: armazenar o hash do SQL de entrada). Se a mesma Procedure for enviada duas vezes, o sistema devolve o código Python gerado anteriormente, poupando tempo e custos (Tokens) da API do LLM.

---

## 8. Execução da Suíte de Testes

Para a execução dos testes automatizados em ambiente local de desenvolvimento (fora da rede Docker):

```bash
# 1. Criação e ativação do ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Ambiente Windows: .venv\Scripts\activate

# 2. Instalação de dependências
pip install -r requirements.txt

# 3. Execução do Pytest
pytest -v
```
