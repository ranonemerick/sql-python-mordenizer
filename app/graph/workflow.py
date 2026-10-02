from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    generate_code_node,
    parse_sql_node,
    semantic_analysis_node,
    validate_code_node,
)
from app.graph.state import ModernizationState

# Inicializa o construtor do grafo injetando o tipo do nosso State
workflow = StateGraph(ModernizationState)

# Adiciona os nós (nome_do_no, funcao_que_executa)
workflow.add_node("parse", parse_sql_node)
workflow.add_node("semantic", semantic_analysis_node)
workflow.add_node("generate", generate_code_node)
workflow.add_node("validate", validate_code_node)

def check_parse_status(state: ModernizationState) -> str:
    parsed_data = state.get("parsed_data")
    if parsed_data and parsed_data.get("status") == "error":
        return END
    return "semantic"

# Define as arestas (ordem de execução)
workflow.add_edge(START, "parse")
workflow.add_conditional_edges(
    "parse",
    check_parse_status,
    {
        "semantic": "semantic",
        END: END
    }
)
workflow.add_edge("semantic", "generate")
workflow.add_edge("generate", "validate")
workflow.add_edge("validate", END)

# Compila o grafo para um executável
modernizer_app = workflow.compile()
