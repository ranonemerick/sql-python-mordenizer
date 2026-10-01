import sqlglot
from sqlglot.errors import ParseError
from sqlglot.expressions import Table

from app.graph.state import ModernizationState


def parse_sql_node(state: ModernizationState) -> dict:
    """Nó 1: Recebe o SQL e gera a estrutura intermediária (AST)."""
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
    """Nó 2: Extrai contexto do parsing e do código para guiar o LLM."""
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
            "CURSOR DETETADO: Perigo de N+1 queries. O LLM deve traduzir para processamento set-based/lotes no SQLAlchemy, evitando iterar a base de dados linha a linha no Python."
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
            "CTE COMPLEXA: Avaliar se deve manter a query no PostgreSQL (via texto/SQLAlchemy Core) para evitar tráfego massivo de dados para a memória Python."
        )
    if has_out_params:
        risk_points.append(
            "PARÂMETROS OUT DETETADOS: Em Python, retornar como um Tuple ou um Dataclass/Pydantic Model, em vez de alterar parâmetros por referência."
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
    print("Executando Node: GENERATION")
    dummy_code = "def converted_function():\n    pass"
    return {"generated_code": dummy_code}


def validate_code_node(state: ModernizationState) -> dict:
    print("Executando Node: VALIDATION")
    report = {"parsing": "ok", "semantic": "ok", "generation": "ok", "validation": "ok"}
    return {"validation_result": {"is_valid": True}, "report": report}
