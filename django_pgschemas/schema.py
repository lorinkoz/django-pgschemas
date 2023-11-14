from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional

from asgiref.sync import sync_to_async

from django_pgschemas.signals import schema_activate


def get_default_schema() -> "Schema":
    return Schema.create("public")


active: ContextVar["Schema"] = ContextVar("active", default=get_default_schema())


def get_current_schema() -> "Schema":
    active.get()


def activate(schema: "Schema"):
    if not isinstance(schema, Schema):
        raise RuntimeError("'activate' must be called with a Schema descendant")

    active.set(schema)

    schema_activate.send(sender=Schema, schema=schema)


def deactivate():
    active.set(get_default_schema())

    schema_activate.send(sender=Schema, schema=Schema.create("public"))


activate_public = deactivate


@contextmanager
def override(schema: "Schema") -> Iterator[None]:
    token = active.set(schema)

    yield

    active.reset(token)


class Schema:
    schema_name = None
    domain_url = None
    folder = None

    is_dynamic = False

    @staticmethod
    def create(schema_name: str, domain_url: Optional[str] = None, folder: Optional[str] = None):
        schema = Schema()
        schema.schema_name = schema_name
        schema.domain_url = domain_url
        schema.folder = folder
        return schema

    def __enter__(self) -> None:
        schema = active.get()
        if schema is not None:
            self._previous_active_token = active.set(self)

    __aenter__ = sync_to_async(__enter__)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        _previous_active_token = getattr(self, "_previous_active_token", None)
        if _previous_active_token is not None:
            active.reset(_previous_active_token)

    __aexit__ = sync_to_async(__exit__)
