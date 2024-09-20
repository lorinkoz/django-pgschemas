import pytest
from django.template import Context, Template

from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.schema import (
    Schema,
    deactivate,
    get_current_schema,
    get_default_schema,
    override,
    shallow_equal,
)


@pytest.mark.parametrize(
    "schema1, schema2, equals",
    [
        (
            get_default_schema(),
            get_default_schema(),
            True,
        ),
        (
            Schema.create("test1"),
            Schema.create("test1"),
            True,
        ),
        (
            Schema.create("test1"),
            Schema.create("test2"),
            False,
        ),
        (
            Schema.create("test1"),
            Schema.create("test1", SessionInfo("ref1")),
            False,
        ),
        (
            Schema.create("test1", HeadersInfo("ref1")),
            Schema.create("test1", SessionInfo("ref1")),
            False,
        ),
        (
            Schema.create("test1", HeadersInfo("ref1")),
            Schema.create("test1", HeadersInfo("ref1")),
            True,
        ),
        (
            Schema.create("test1", DomainInfo("domain1")),
            Schema.create("test1", DomainInfo("domain1", "folder")),
            False,
        ),
        (
            Schema.create("test1", DomainInfo("domain1", "folder")),
            Schema.create("test1", DomainInfo("domain1", "folder")),
            True,
        ),
    ],
)
def test_shallow_equal(schema1, schema2, equals):
    assert shallow_equal(schema1, schema2) == equals


def test_nested_override():
    deactivate()

    schema1 = Schema.create(schema_name="schema_1")
    schema2 = Schema.create(schema_name="schema_2")

    assert get_current_schema().schema_name == get_default_schema().schema_name

    with override(schema1):
        assert get_current_schema().schema_name == schema1.schema_name

        with override(schema2):
            assert get_current_schema().schema_name == schema2.schema_name

            with override(schema1):
                assert get_current_schema().schema_name == schema1.schema_name

            assert get_current_schema().schema_name == schema2.schema_name

        assert get_current_schema().schema_name == schema1.schema_name

    assert get_current_schema().schema_name == get_default_schema().schema_name


def test_nested_class_override():
    deactivate()

    schema1 = Schema.create(schema_name="schema_1")
    schema2 = Schema.create(schema_name="schema_2")

    assert get_current_schema().schema_name == get_default_schema().schema_name

    with schema1:
        assert get_current_schema().schema_name == schema1.schema_name

        with schema2:
            assert get_current_schema().schema_name == schema2.schema_name

            with schema1:
                assert get_current_schema().schema_name == schema1.schema_name

            assert get_current_schema().schema_name == schema2.schema_name

        assert get_current_schema().schema_name == schema1.schema_name

    assert get_current_schema().schema_name == get_default_schema().schema_name


def test_schema_is_template_renderable():
    schema = Schema.create(schema_name="template_schema")

    context = Context({"schema": schema})
    template = Template("{{ schema.schema_name }}")

    rendered = template.render(context)

    assert rendered == "template_schema"
