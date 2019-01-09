from django.core import management
from django.core.management.base import BaseCommand
from django.core.management.commands.migrate import Command as MigrateCommand

from . import WrappedSchemaOption
from .runschema import Command as RunSchemaCommand


class NonInteractiveRunSchemaCommand(RunSchemaCommand):
    allow_interactive = False


class MigrateSchemaCommand(WrappedSchemaOption, BaseCommand):
    allow_interactive = False

    def add_arguments(self, parser):
        super().add_arguments(parser)
        MigrateCommand.add_arguments(self, parser)

    def handle(self, *args, **options):
        runschema = NonInteractiveRunSchemaCommand()
        options.pop("run_syncdb", False)
        runschema.execute(command_name="django.core.migrate", *args, **options)


Command = MigrateSchemaCommand
