from contextlib import contextmanager
from contextvars import ContextVar, Token
from functools import lru_cache
from typing import Iterator

from django_pgschemas.routing.info import RoutingInfo
from django_pgschemas.signals import schema_activate


class Schema:
    schema_name: str
    routing: RoutingInfo = None

    is_dynamic = False

    _context_tokens: list[Token["Schema"] | None]

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._context_tokens = []

    @staticmethod
    def create(schema_name: str, routing: RoutingInfo | None = None) -> "Schema":
        schema = Schema()
        schema.schema_name = schema_name
        schema.routing = routing
        return schema

    def __enter__(self) -> None:
        self._context_tokens.append(push(self))

    def __exit__(self, *args: object) -> None:
        if self._context_tokens:
            token = self._context_tokens.pop()
            if token is not None:
                active.reset(token)


def shallow_equal(schema1: Schema, schema2: Schema) -> bool:
    return schema1.schema_name == schema2.schema_name and schema1.routing == schema2.routing


@lru_cache
def get_default_schema() -> Schema:
    return Schema.create("public")


active: ContextVar["Schema"] = ContextVar("active_schema", default=get_default_schema())


def get_current_schema() -> Schema:
    return active.get()


def push(schema: Schema) -> Token[Schema] | None:
    if shallow_equal(get_current_schema(), schema):
        return None

    token = active.set(schema)

    schema_activate.send(sender=Schema, schema=schema)

    return token


def activate(schema: Schema) -> None:
    push(schema)


def deactivate() -> None:
    push(get_default_schema())


activate_public = deactivate


@contextmanager
def override(schema: Schema) -> Iterator[None]:
    token = push(schema)

    yield

    if token is not None:
        active.reset(token)
