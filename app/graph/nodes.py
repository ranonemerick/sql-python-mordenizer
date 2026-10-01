from app.graph.state import ModernizationState


def parse_sql_node(state: ModernizationState) -> dict:
    print("Executando Node: PARSING")
    return {"parsed_data": {"status": "parsed_dummy"}}


def semantic_analysis_node(state: ModernizationState) -> dict:
    print("Executando Node: SEMANTIC ANALYSIS")
    return {"semantic_analysis": {"variables": [], "risk_points": []}}


def generate_code_node(state: ModernizationState) -> dict:
    print("Executando Node: GENERATION")
    dummy_code = "def converted_function():\n    pass"
    return {"generated_code": dummy_code}


def validate_code_node(state: ModernizationState) -> dict:
    print("Executando Node: VALIDATION")
    report = {"parsing": "ok", "semantic": "ok", "generation": "ok", "validation": "ok"}
    return {"validation_result": {"is_valid": True}, "report": report}
