from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import Base, engine, get_db
from app.graph.workflow import modernizer_app
from app.models.history import ModernizationHistory

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
    schema_sql: str | None = None  # Aceita nulo/opcional


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
    initial_state = {
        "source_code": request.source_code,
        "parsed_data": None,
        "semantic_analysis": None,
        "generated_code": None,
        "validation_result": None,
        "report": {},
        "errors": [],
    }

    final_state = modernizer_app.invoke(initial_state)

    return ModernizeResponse(
        status="success",
        generated_code=final_state.get("generated_code"),
        report=final_state.get("report"),
    )
