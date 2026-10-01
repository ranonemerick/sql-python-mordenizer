import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/modernizer"
)

# Cria a "Engine" (o Pool de conexões JDBC)
engine = create_engine(DATABASE_URL)

# Cria a fábrica de sessões (EntityManager)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base genérica para as entidades anotadas
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
