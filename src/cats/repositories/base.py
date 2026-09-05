from typing import Generic, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class Repository(Generic[T]):
    def __init__(self, session: Session, model_type: type[T]):
        self.session = session
        self.model_type = model_type

    def get(self, object_id: str) -> T | None:
        return self.session.get(self.model_type, object_id)

    def add(self, obj: T) -> T:
        self.session.add(obj)
        return obj
