from __future__ import annotations

import argparse
import json

from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.runtime.post_run_verifier import PostRunVerifier


def main():
    parser = argparse.ArgumentParser(description="Verify one persisted CATS PAPER flow.")
    parser.add_argument("--flow-id", required=True)
    args = parser.parse_args()

    engine = create_engine_from_settings(get_settings())
    Session = create_session_factory(engine)
    with Session() as session:
        result = PostRunVerifier(session).verify(args.flow_id)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
