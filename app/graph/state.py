from typing import Any, Optional, TypedDict


class ModernizationState(TypedDict):
    source_code: str
    parsed_data: Optional[Any]
    semantic_analysis: Optional[Any]
    generated_code: Optional[str]
    validation_result: Optional[dict]
    report: dict
    errors: list[str]
