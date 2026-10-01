from sqlalchemy.orm import Session

from app.models.history import ModernizationHistory


def create_execution(db: Session, source_code: str) -> ModernizationHistory:
    db_record = ModernizationHistory(source_code=source_code, status="RUNNING")
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def update_execution(
    db: Session,
    record_id: str,
    status: str,
    generated_code: str = None,
    report: dict = None,
) -> ModernizationHistory:
    db_record = (
        db.query(ModernizationHistory)
        .filter(ModernizationHistory.id == record_id)
        .first()
    )

    if db_record:
        db_record.status = status
        if generated_code is not None:
            db_record.generated_code = generated_code
        if report is not None:
            db_record.report = report

        db.commit()
        db.refresh(db_record)

    return db_record
