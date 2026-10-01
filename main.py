from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import Base, engine, get_db
from app.models.history import ModernizationHistory

# Cria as tabelas fisicamente no banco de dados
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SQL to Python Modernizer",
    description="Pipeline híbrido de modernização PL/pgSQL para Python",
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    """
    O parâmetro Depends(get_db) diz ao FastAPI para injetar a conexão.
    """
    count = db.query(ModernizationHistory).count()
    return {"message": "Conexão com PostgreSQL bem sucedida!", "history_count": count}
