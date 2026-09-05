from __future__ import annotations

import json

from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.database import models
from cats.runtime.post_run_verifier import PostRunVerifier


def main():
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    Session = create_session_factory(engine)

    with Session() as session:
        flow = (
            session.query(models.TraceFlow)
            .order_by(models.TraceFlow.started_at.desc())
            .first()
        )
        if flow is None:
            raise SystemExit("No TRACE_Flow records exist.")

        result = PostRunVerifier(session).verify(flow.flow_id)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
