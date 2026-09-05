from alembic import command
from alembic.config import Config

from cats.configuration import get_settings


def main():
    settings = get_settings()
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    print("Database migrations: PASS")


if __name__ == "__main__":
    main()
