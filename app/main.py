from fastapi import Depends, FastAPI
from langfuse.langchain import CallbackHandler
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import Base, engine, get_db
from app.graph.workflow import modernizer_app
from app.models.history import ModernizationHistory
from app.repositories import history_repository

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SQL to Python Modernizer",
    description="Pipeline híbrido de modernização PL/pgSQL para Python",
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str


class ModernizeRequest(BaseModel):
    source_code: str
    schema_sql: str | None = None


class ModernizeResponse(BaseModel):
    id: str | None = None
    status: str
    generated_code: str | None = None
    report: dict | None = None


@app.get("/health", response_model=HealthResponse)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    count = db.query(ModernizationHistory).count()
    return {"message": "Conexão com PostgreSQL bem sucedida!", "history_count": count}


@app.post("/modernize", response_model=ModernizeResponse)
def modernize_sql(request: ModernizeRequest, db: Session = Depends(get_db)):

    execution_record = history_repository.create_execution(db, request.source_code)

    initial_state = {
        "source_code": request.source_code,
        "parsed_data": None,
        "semantic_analysis": None,
        "generated_code": None,
        "validation_result": None,
        "report": {},
        "errors": [],
    }

    langfuse_handler = CallbackHandler()

    final_state = modernizer_app.invoke(
        initial_state, config={"callbacks": [langfuse_handler]}
    )

    report = final_state.get("report", {})
    validation_status = report.get("validation_status", "")
    pipeline_errors = final_state.get("errors", [])

    if "SUCCESS" in validation_status and len(pipeline_errors) == 0:
        final_status = "success"
    else:
        final_status = "failed"
        report["pipeline_errors"] = final_state.get("errors", [])

    generated_code = final_state.get("generated_code")

    history_repository.update_execution(
        db=db,
        record_id=execution_record.id,
        status=final_status,
        generated_code=generated_code,
        report=report,
    )

    return ModernizeResponse(
        id=execution_record.id,
        status=final_status,
        generated_code=generated_code,
        report=report,
    )
