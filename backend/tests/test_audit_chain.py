import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.audit.service import record_audit_event, verify_audit_chain
from app.database import Base
from app.models import AuditLog


@pytest.fixture
def audit_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        yield db

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_valid_audit_chain_passes_verification(audit_db):
    record_audit_event(
        audit_db,
        actor_id=None,
        action="document.upload",
        resource_type="document",
        resource_id="101",
        outcome="success",
        details="First event",
    )
    record_audit_event(
        audit_db,
        actor_id=None,
        action="document.download",
        resource_type="document",
        resource_id="101",
        outcome="success",
        details="Second event",
    )
    audit_db.commit()

    assert verify_audit_chain(audit_db) is True


def test_modified_audit_event_fails_verification(audit_db):
    event = record_audit_event(
        audit_db,
        actor_id=None,
        action="document.download",
        resource_type="document",
        resource_id="101",
        outcome="success",
        details="Original details",
    )
    audit_db.commit()

    event.details = "Modified details"
    audit_db.commit()

    assert verify_audit_chain(audit_db) is False
