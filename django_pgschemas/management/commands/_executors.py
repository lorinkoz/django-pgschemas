import sys

from django.core.management import color
from django.core.management.base import OutputWrapper
from django.db import connection


def run_on_schema(schema_name, executor_codename, command, command_caller):
    style = color.color_style()

    def style_func(message):
        return "[%s:%s] %s" % (style.NOTICE(executor_codename), style.NOTICE(schema_name), message)

    command.stdout = OutputWrapper(sys.stdout)
    command.stderr = OutputWrapper(sys.stderr)
    command.stdout.style_func = command.stderr.style_func = style_func
    command_caller(command, schema_name)


def standard(schemas, command, command_caller):
    current_schema = getattr(connection, "schema_name", "public")
    for schema in schemas:
        connection.set_schema(schema)
        run_on_schema(schema, "standard", command, command_caller)
    connection.set_schema(current_schema)


def multiproc(schemas, command, command_caller):
    pass
