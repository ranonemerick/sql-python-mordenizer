from sqlalchemy import text
from app.config.database import engine
with engine.connect() as conn:
    conn.execute(text('DROP TABLE IF EXISTS modernization_history CASCADE'))
    conn.commit()
