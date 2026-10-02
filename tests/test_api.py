import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    """Garante que o servidor está de pé e responde corretamente."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_modernize_endpoint_invalid_payload():
    """
    Garante que a validação do Pydantic bloqueia requisições malformadas.
    Em Java seria o @Valid a devolver 400 Bad Request. O FastAPI devolve 422.
    """
    response = client.post("/modernize", json={"outra_chave_qualquer": "SELECT *"})
    assert response.status_code == 422


def test_modernize_endpoint_parsing_error():
    """
    Testa a resiliência do pipeline LangGraph.
    Enviamos um SQL deliberadamente quebrado. A aplicação não deve fazer 'crash' (500),
    mas sim processar a falha graciosamente e devolver status="failed".
    """
    payload = {"source_code": "SELECT * FROM BLABLABLA WHERE;;;;;  "}

    response = client.post("/modernize", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "failed"
    assert "id" in data
    assert "Erro de parsing no sqlglot" in data["report"]["pipeline_errors"][0]
