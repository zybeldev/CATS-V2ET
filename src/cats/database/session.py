from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from cats.configuration import Settings


def create_engine_from_settings(settings: Settings) -> Engine:
    return create_engine(settings.database_url, future=True)


def create_session_factory(engine: Engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
