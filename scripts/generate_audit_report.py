from __future__ import annotations

import argparse
from pathlib import Path

from cats.configuration import get_settings
from cats.database import create_engine_from_settings, create_session_factory
from cats.database import models
from cats.runtime.audit_report import AuditReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate CATS PAPER audit report.")
    parser.add_argument("--flow-id")
    parser.add_argument("--output-dir", default="run_reports")
    args = parser.parse_args()

    engine = create_engine_from_settings(get_settings())
    Session = create_session_factory(engine)

    with Session() as session:
        flow_id = args.flow_id
        if not flow_id:
            latest = (
                session.query(models.TraceFlow)
                .order_by(models.TraceFlow.started_at.desc())
                .first()
            )
            if latest is None:
                raise SystemExit("No TRACE_Flow records exist.")
            flow_id = latest.flow_id

        generator = AuditReportGenerator(session)
        output = Path(args.output_dir)
        json_path = generator.write_json(flow_id, output / f"CATS_{flow_id}_audit.json")
        md_path = generator.write_markdown(flow_id, output / f"CATS_{flow_id}_audit.md")

        print(f"Audit JSON: {json_path}")
        print(f"Audit Markdown: {md_path}")


if __name__ == "__main__":
    main()
