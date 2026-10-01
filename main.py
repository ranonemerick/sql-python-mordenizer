from fastapi import FastAPI
from pydantic import BaseModel

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
