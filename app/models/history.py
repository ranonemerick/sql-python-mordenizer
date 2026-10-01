import uuid

from sqlalchemy import Column, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB

from app.config.database import Base


class ModernizationHistory(Base):
    __tablename__ = "modernization_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_code = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=True)
    report = Column(JSONB, nullable=True)
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
