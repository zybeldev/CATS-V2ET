from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cats.database.base import Base
from cats.database import models
from cats.runtime.post_run_verifier import PostRunVerificationError, PostRunVerifier


def test_post_run_verifier_fails_closed_for_incomplete_completed_flow():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        environment_id = str(uuid4())
        flow_id = str(uuid4())
        session.add(models.Environment(
            environment_id=environment_id,
            environment_code="PAPER",
            name="Paper",
            is_active=True,
        ))
        session.add(models.TraceFlow(
            flow_id=flow_id,
            environment_id=environment_id,
            flow_type="TEST",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status="COMPLETED",
        ))
        session.commit()

        with pytest.raises(PostRunVerificationError, match="incomplete"):
            PostRunVerifier(session).verify(flow_id)
