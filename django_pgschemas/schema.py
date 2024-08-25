from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from asgiref.sync import sync_to_async

from django_pgschemas.routing.info import RoutingInfo
from django_pgschemas.signals import schema_activate


class Schema:
    schema_name: str
    routing: RoutingInfo = None

    is_dynamic = False

    @staticmethod
    def create(schema_name: str, routing: RoutingInfo | None = None) -> "Schema":
        schema = Schema()
        schema.schema_name = schema_name
        schema.routing = routing
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


def get_default_schema() -> Schema:
    return Schema.create("public")


active: ContextVar["Schema"] = ContextVar("active", default=get_default_schema())


def get_current_schema() -> Schema:
    return active.get()


def activate(schema: Schema) -> None:
    active.set(schema)

    schema_activate.send(sender=Schema, schema=schema)


def deactivate() -> None:
    active.set(get_default_schema())

    schema_activate.send(sender=Schema, schema=Schema.create("public"))


activate_public = deactivate


@contextmanager
def override(schema: Schema) -> Iterator[None]:
    token = active.set(schema)

    yield

    active.reset(token)
