import ast
import json
import os

import sqlglot
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlglot.errors import ParseError
from sqlglot.expressions import Table

from app.graph.state import ModernizationState

load_dotenv()


# ==========================================
# DTOs
# ==========================================
class LLMGenerationOutput(BaseModel):
    python_code: str = Field(
        description="O código Python 3.14 gerado, limpo, sem marcação markdown."
    )
    explanation: str = Field(
        description="Explicação passo a passo de como o código funciona."
    )
    translation_decisions: list[str] = Field(
        description="Lista de decisões técnicas tomadas na tradução."
    )
    limitations: list[str] = Field(
        description="Limitações identificadas, como SQL que precisou ficar bruto."
    )


# ==========================================
# Nodes do LangGraph
# ==========================================


def parse_sql_node(state: ModernizationState) -> dict:
    print("Executando Node: PARSING")
    source_code = state.get("source_code", "")

    try:
        expressions = sqlglot.parse(source_code, read="postgres")
        parsed_statements = []
        for expr in expressions:
            if expr:
                parsed_statements.append(
                    {
                        "type": type(expr).__name__,
                        "sql_reconstruido": expr.sql(dialect="postgres"),
                    }
                )

        return {
            "parsed_data": {
                "status": "success",
                "statements": parsed_statements,
                "statement_count": len(parsed_statements),
            }
        }
    except ParseError as e:
        error_msg = f"Erro de parsing no sqlglot: {str(e)}"
        print(error_msg)
        current_errors = state.get("errors", [])
        current_errors.append(error_msg)
        return {
            "parsed_data": {"status": "error", "statements": []},
            "errors": current_errors,
        }


def semantic_analysis_node(state: ModernizationState) -> dict:
    print("Executando Node: SEMANTIC ANALYSIS")
    source_code = state.get("source_code", "")
    source_upper = source_code.upper()
    tables_used = set()

    try:
        for expression in sqlglot.parse(source_code, read="postgres"):
            if expression:
                for table in expression.find_all(Table):
                    tables_used.add(table.name)
    except Exception:
        pass

    has_cursor = "CURSOR FOR" in source_upper or "FETCH " in source_upper
    has_exception = "EXCEPTION" in source_upper and "WHEN " in source_upper
    has_loop = "LOOP" in source_upper and "END LOOP" in source_upper
    has_transaction = "FOR UPDATE" in source_upper or "COMMIT" in source_upper
    has_json = "JSONB" in source_upper or "JSON_" in source_upper
    has_cte = "WITH RECURSIVE" in source_upper or "WITH " in source_upper
    has_out_params = "OUT " in source_upper

    risk_points = []
    if has_cursor:
        risk_points.append(
            "CURSOR DETETADO: Perigo de N+1 queries. O LLM deve traduzir para processamento set-based/lotes no SQLAlchemy."
        )
    if has_exception:
        risk_points.append(
            "EXCEPTION DETETADA: Traduzir para blocos try/except em Python com session.rollback()."
        )
    if has_transaction:
        risk_points.append(
            "TRANSAÇÃO (FOR UPDATE) DETETADA: A concorrência deve ser gerida via SQLAlchemy explicitamente."
        )
    if has_cte:
        risk_points.append(
            "CTE COMPLEXA: Avaliar se deve manter a query no PostgreSQL (via SQLAlchemy Core)."
        )
    if has_out_params:
        risk_points.append(
            "PARÂMETROS OUT DETETADOS: Retornar como um Tuple ou Pydantic Model."
        )

    complexity = (
        "Alta/Muito Alta"
        if (has_cursor or has_cte)
        else ("Média" if has_transaction or has_exception else "Baixa")
    )

    semantic_context = {
        "tables_used": list(tables_used),
        "features": {
            "has_cursor": has_cursor,
            "has_exception": has_exception,
            "has_loop": has_loop,
            "has_transaction": has_transaction,
            "has_json": has_json,
            "has_recursive_cte": has_cte,
            "has_out_params": has_out_params,
        },
        "risk_points": risk_points,
        "estimated_complexity": complexity,
    }
    return {"semantic_analysis": semantic_context}


def generate_code_node(state: ModernizationState) -> dict:
    print("Executando Node: GENERATION (Gemini Raw JSON)")
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or api_key == "CHAVE AQUI":
        print("AVISO: Chave do Gemini ausente.")
        return {"generated_code": "def mock_function():\n    pass"}

    source_code = state.get("source_code", "")
    semantic_data = state.get("semantic_analysis", {})
    risk_points = semantic_data.get("risk_points", [])

    # Voltamos ao modelo gemini-1.5-flash sem o wrapper de structured output
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.8-flash", temperature=0.1, google_api_key=api_key
    )

    # Adaptamos o prompt para forçar o JSON no texto de resposta
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Você é um Arquiteto de Software Sênior especialista em modernizar código legado PL/pgSQL para Python 3.14 (usando SQLAlchemy 2.0).
        Regras cruciais:
        - Se a operação for um processamento em lote, prefira SQL set-based e SQLAlchemy bulk operations no lugar de carregar tudo em memória.
        - Trate transações adequadamente usando a Session do SQLAlchemy (commit/rollback).
        - Os parâmetros de entrada do Python devem ter type hints.
        - Atenha-se aos pontos de risco indicados pela análise semântica.
        
        MUITO IMPORTANTE:
        Você DEVE retornar APENAS um JSON válido. Não adicione texto antes nem depois. Não use blocos de formatação markdown (como ```json).
        O JSON deve ter EXATAMENTE este formato:
        {{
            "python_code": "string com o código python",
            "explanation": "string com a explicação",
            "translation_decisions": ["decisao 1", "decisao 2"],
            "limitations": ["limitacao 1"]
        }}
        """,
            ),
            (
                "user",
                """Por favor, modernize a seguinte procedure PL/pgSQL.
        [CÓDIGO ORIGINAL]
        {source_code}
        [PONTOS DE RISCO]
        {risk_points}""",
            ),
        ]
    )

    try:
        # Adicionamos o StrOutputParser no final do pipeline
        chain = prompt | llm | StrOutputParser()

        # Agora a resposta já é garantidamente uma String
        raw_text = chain.invoke(
            {
                "source_code": source_code,
                "risk_points": "\n".join(risk_points)
                if risk_points
                else "Nenhum ponto crítico.",
            }
        )

        # Limpa possível sujeira do LLM (markdown)
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        # Converte de String para Dicionário
        parsed_json = json.loads(raw_text)

        partial_report = {
            "explanation": parsed_json.get("explanation", ""),
            "decisions": parsed_json.get("translation_decisions", []),
            "limitations": parsed_json.get("limitations", []),
        }
        return {
            "generated_code": parsed_json.get("python_code"),
            "report": partial_report,
        }

    except json.JSONDecodeError as e:
        error_msg = f"Falha ao interpretar o JSON retornado pelo LLM: {str(e)}\nRetorno bruto: {raw_text}"
        print(error_msg)
        return {"generated_code": None, "errors": state.get("errors", []) + [error_msg]}
    except Exception as e:
        error_msg = f"Falha na geração LLM: {str(e)}"
        print(error_msg)
        return {"generated_code": None, "errors": state.get("errors", []) + [error_msg]}


def validate_code_node(state: ModernizationState) -> dict:
    print("Executando Node: VALIDATION")

    generated_code = state.get("generated_code")
    current_report = state.get("report", {})  # Recupera o relatório criado no nó 3
    current_errors = state.get("errors", [])

    if not generated_code:
        current_report["validation_status"] = "FAILED: Nenhum código gerado"
        return {"validation_result": {"is_valid": False}, "report": current_report}

    try:
        # Tenta compilar a string para a árvore sintática do Python
        # Se houver erro de indentação, parênteses ou sintaxe, lança SyntaxError
        ast.parse(generated_code)

        current_report["validation_status"] = "SUCCESS"
        return {"validation_result": {"is_valid": True}, "report": current_report}

    except SyntaxError as e:
        error_msg = f"Erro de sintaxe no código gerado: {str(e)}"
        print(error_msg)
        current_errors.append(error_msg)

        current_report["validation_status"] = "FAILED: Syntax Error"
        current_report["syntax_error_details"] = str(e)

        return {
            "validation_result": {"is_valid": False},
            "report": current_report,
            "errors": current_errors,
        }
