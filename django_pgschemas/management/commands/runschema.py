import argparse
import sys

from django.core.management import get_commands, load_command_class
from django.core.management.base import BaseCommand, CommandError, SystemCheckError

from . import WrappedSchemaOption


class Command(WrappedSchemaOption, BaseCommand):
    help = "Wrapper around Django commands for use with an individual schema"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("command_name", help="The command name you want to run")

    def get_command_from_arg(self, arg):
        *chunks, command = arg.split(".")
        path = ".".join(chunks)
        if not path:
            path = get_commands().get(command)
        try:
            cmd = load_command_class(path, command)
        except Exception:
            raise CommandError("Unknown command: %s" % arg)
        if isinstance(cmd, WrappedSchemaOption):
            raise CommandError("Command '%s' cannot be used in runschema" % arg)
        return cmd

    def run_from_argv(self, argv):  # pragma: no cover
        """
        Changes the option_list to use the options from the wrapped command.
        Adds schema parameter to specify which schema will be used when
        executing the wrapped command.
        """
        try:
            # load the command object.
            if len(argv) <= 2:
                raise CommandError("No command to run")
            target_class = self.get_command_from_arg(argv[2])
            # Ugly, but works. Delete command_name from the argv, parse the schemas manually
            # and forward the rest of the arguments to the actual command being wrapped.
            del argv[1]
            schema_parser = argparse.ArgumentParser()
            super().add_arguments(schema_parser)
            schema_ns, args = schema_parser.parse_known_args(argv)

            schemas = self.get_schemas_from_options(
                schemas=schema_ns.schemas,
                all_schemas=schema_ns.all_schemas,
                static_schemas=schema_ns.static_schemas,
                dynamic_schemas=schema_ns.dynamic_schemas,
                tenant_schemas=schema_ns.tenant_schemas,
            )
            executor = self.get_executor_from_options(parallel=schema_ns.parallel)
        except Exception as e:
            if not isinstance(e, CommandError):
                raise
            # SystemCheckError takes care of its own formatting.
            if isinstance(e, SystemCheckError):
                self.stderr.write(str(e), lambda x: x)
            else:
                self.stderr.write("%s: %s" % (e.__class__.__name__, e))
            sys.exit(1)

        executor(schemas, target_class, "special:run_from_argv", args)

    def handle(self, *args, **options):
        target = self.get_command_from_arg(options.pop("command_name"))
        schemas = self.get_schemas_from_options(**options)
        executor = self.get_executor_from_options(**options)
        options.pop("schemas")
        options.pop("excluded_schemas")
        options.pop("all_schemas")
        options.pop("static_schemas")
        options.pop("dynamic_schemas")
        options.pop("tenant_schemas")
        options.pop("parallel")
        options.pop("skip_schema_creation")
        if self.allow_interactive:
            options.pop("interactive")
        executor(schemas, target, "special:call_command", args, options)
