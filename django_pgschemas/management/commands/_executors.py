import functools
import multiprocessing
import sys

from django.conf import settings
from django.core.management import call_command, color
from django.core.management.base import OutputWrapper, CommandError


def run_on_schema(
    schema_name, executor_codename, command_class, function_name=None, args=[], kwargs={}, pass_schema_in_kwargs=False
):
    from django.db import connection

    style = color.color_style()
    stdout = OutputWrapper(sys.stdout)
    stderr = OutputWrapper(sys.stderr)
    stdout.style_func = stderr.style_func = lambda message: "[%s:%s] %s" % (
        style.NOTICE(executor_codename),
        style.NOTICE(schema_name),
        message,
    )
    command = command_class(stdout=stdout, stderr=stderr)

    connection.set_schema(schema_name)
    if pass_schema_in_kwargs:
        kwargs.update({"schema_name": schema_name})
    if function_name == "special:call_command":
        call_command(command, *args, **kwargs)
    elif function_name == "special:run_from_argv":
        command.run_from_argv(args)
    else:
        getattr(command, function_name)(*args, **kwargs)


def sequential(schemas, command_class, function_name, args=[], kwargs={}, pass_schema_in_kwargs=False):
    runner = functools.partial(
        run_on_schema,
        executor_codename="sequential",
        command_class=command_class,
        function_name=function_name,
        args=args,
        kwargs=kwargs,
        pass_schema_in_kwargs=pass_schema_in_kwargs,
    )
    map(runner, schemas)


def parallel(schemas, command_class, function_name, args=[], kwargs={}, pass_schema_in_kwargs=False):
    raise CommandError("Parallel executor is not ready to be used yet")
    processes = getattr(settings, "PGSCHEMAS_MULTIPROCESSING_MAX_PROCESSES", None)
    pool = multiprocessing.Pool(processes=processes)
    runner = functools.partial(
        run_on_schema,
        executor_codename="parallel",
        command_class=command_class,
        function_name=function_name,
        args=args,
        kwargs=kwargs,
        pass_schema_in_kwargs=pass_schema_in_kwargs,
    )
    pool.map(runner, schemas, 1)
