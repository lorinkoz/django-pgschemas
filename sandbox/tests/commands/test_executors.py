from typing import Any, ClassVar
from unittest.mock import patch

import pytest
from django.core import management
from django.core.management.base import CommandError

from django_pgschemas.management.commands import CommandScope, SchemaCommand
from django_pgschemas.management.commands._executors import parallel, sequential
from django_pgschemas.schema import Schema


class RecordingSchemaCommand(SchemaCommand):
    """Deterministic SchemaCommand used to exercise executor failure paths."""

    scope = CommandScope.STATIC
    allow_interactive = False
    fail_on: ClassVar[set[str]] = set()
    completed: ClassVar[list[str]] = []
    started: ClassVar[list[str]] = []

    @classmethod
    def reset(cls, fail_on: set[str] | None = None) -> None:
        cls.fail_on = set(fail_on or ())
        cls.completed = []
        cls.started = []

    def handle_schema(self, schema: Schema, *args: Any, **options: Any) -> None:
        type(self).started.append(schema.schema_name)
        if schema.schema_name in type(self).fail_on:
            raise RuntimeError(f"boom:{schema.schema_name}")
        type(self).completed.append(schema.schema_name)


@pytest.fixture(autouse=True)
def _reset_recording_command():
    RecordingSchemaCommand.reset()
    yield
    RecordingSchemaCommand.reset()


def test_sequential_raises_original_error_and_stops():
    RecordingSchemaCommand.fail_on = {"blog"}

    with pytest.raises(RuntimeError, match=r"boom:blog"):
        sequential(
            ["blog", "www"],
            RecordingSchemaCommand(),
            "_raw_handle_schema",
            args=[],
            kwargs={},
            pass_schema_in_kwargs=True,
        )

    assert RecordingSchemaCommand.started == ["blog"]
    assert RecordingSchemaCommand.completed == []


def test_parallel_raises_command_error_for_single_failure():
    RecordingSchemaCommand.fail_on = {"blog"}

    with pytest.raises(CommandError) as ctx:
        parallel(
            ["www", "blog"],
            RecordingSchemaCommand(),
            "_raw_handle_schema",
            args=[],
            kwargs={},
            pass_schema_in_kwargs=True,
        )

    message = str(ctx.value)
    assert "schema blog" in message
    assert "boom:blog" in message
    assert ctx.value.__cause__ is not None
    assert str(ctx.value.__cause__) == "boom:blog"

    # Non-failing schemas still complete; parallel does not abort early.
    assert set(RecordingSchemaCommand.started) == {"www", "blog"}
    assert RecordingSchemaCommand.completed == ["www"]


def test_parallel_aggregates_multiple_failures():
    RecordingSchemaCommand.fail_on = {"blog", "www"}

    with pytest.raises(CommandError) as ctx:
        parallel(
            ["public", "www", "blog"],
            RecordingSchemaCommand(),
            "_raw_handle_schema",
            args=[],
            kwargs={},
            pass_schema_in_kwargs=True,
        )

    message = str(ctx.value)
    assert "2 schemas" in message
    assert "blog: boom:blog" in message
    assert "www: boom:www" in message
    assert message.index("blog:") < message.index("www:")

    assert set(RecordingSchemaCommand.started) == {"public", "www", "blog"}
    assert RecordingSchemaCommand.completed == ["public"]


def test_parallel_closes_connections_per_worker_even_on_failure():
    RecordingSchemaCommand.fail_on = {"blog"}

    with patch(
        "django_pgschemas.management.commands._executors.connections.close_all"
    ) as close_all:
        with pytest.raises(CommandError):
            parallel(
                ["www", "blog"],
                RecordingSchemaCommand(),
                "_raw_handle_schema",
                args=[],
                kwargs={},
                pass_schema_in_kwargs=True,
            )

    assert close_all.call_count == 2


@pytest.mark.django_db
def test_parallel_via_call_command_surfaces_failure():
    RecordingSchemaCommand.fail_on = {"blog"}

    with pytest.raises(CommandError) as ctx:
        management.call_command(
            RecordingSchemaCommand(),
            schemas=["www", "blog"],
            parallel=True,
            verbosity=0,
            skip_schema_creation=True,
        )

    # SchemaCommand --parallel must not exit 0 when a schema fails.
    assert "boom:blog" in str(ctx.value)
    assert set(RecordingSchemaCommand.started) == {"www", "blog"}
    assert RecordingSchemaCommand.completed == ["www"]
