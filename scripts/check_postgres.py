from sqlalchemy import text

from cats.configuration import get_settings
from cats.database import create_engine_from_settings


def main():
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    with engine.connect() as conn:
        value = conn.scalar(text("select 1"))
    print(f"PostgreSQL connectivity: PASS ({value})")


if __name__ == "__main__":
    main()
