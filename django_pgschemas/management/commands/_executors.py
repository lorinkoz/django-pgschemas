import functools
import multiprocessing

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, OutputWrapper, CommandError
from django.db import connection, transaction, connections


def run_on_schema(
    schema_name, executor_codename, command, function_name=None, args=[], kwargs={}, pass_schema_in_kwargs=False
):
    if not isinstance(command, BaseCommand):
        # Parallel executor needs to pass command 'type' instead of 'instance'
        # Therefore, no customizations for the command can be done, nor using custom stdout, stderr
        command = command()

    if not isinstance(command.stdout, OutputWrapper):
        command.stdout = OutputWrapper(command.stdout)
    if not isinstance(command.stderr, OutputWrapper):
        command.stderr = OutputWrapper(command.stderr)

    command.stdout.style_func = command.stderr.style_func = lambda message: "[%s:%s] %s" % (
        command.style.NOTICE(executor_codename),
        command.style.NOTICE(schema_name),
        message,
    )

    connections.close_all()
    connection.set_schema_to(schema_name)
    if pass_schema_in_kwargs:
        kwargs.update({"schema_name": schema_name})
    if function_name == "special:call_command":
        call_command(command, *args, **kwargs)
    elif function_name == "special:run_from_argv":
        command.run_from_argv(args)
    else:
        getattr(command, function_name)(*args, **kwargs)

    transaction.commit()
    connection.close()

    return schema_name


def sequential(schemas, command, function_name, args=[], kwargs={}, pass_schema_in_kwargs=False):
    runner = functools.partial(
        run_on_schema,
        executor_codename="sequential",
        command=command,
        function_name=function_name,
        args=args,
        kwargs=kwargs,
        pass_schema_in_kwargs=pass_schema_in_kwargs,
    )
    for schema in schemas:
        runner(schema)
    return schemas


def parallel(schemas, command, function_name, args=[], kwargs={}, pass_schema_in_kwargs=False):
    processes = getattr(settings, "PGSCHEMAS_PARALLEL_MAX_PROCESSES", None)
    pool = multiprocessing.Pool(processes=processes)
    runner = functools.partial(
        run_on_schema,
        executor_codename="parallel",
        command=type(command),  # Can't pass streams to children processes
        function_name=function_name,
        args=args,
        kwargs=kwargs,
        pass_schema_in_kwargs=pass_schema_in_kwargs,
    )
    return pool.map(runner, schemas)
