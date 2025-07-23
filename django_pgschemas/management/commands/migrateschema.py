from django.core.checks import Tags, run_checks
from django.core.management.base import BaseCommand
from django.core.management.commands.migrate import Command as MigrateCommand
from django.db.migrations.autodetector import MigrationAutodetector

from . import WrappedSchemaOption
from .runschema import Command as RunSchemaCommand


class NonInteractiveRunSchemaCommand(RunSchemaCommand):
    allow_interactive = False


class MigrateSchemaCommand(WrappedSchemaOption, BaseCommand):
    autodetector = MigrationAutodetector
    allow_interactive = False
    requires_system_checks = []

    def _run_checks(self, **kwargs):  # pragma: no cover
        issues = run_checks(tags=[Tags.database])
        issues.extend(super()._run_checks(**kwargs))
        return issues

    def add_arguments(self, parser):
        super().add_arguments(parser)
        MigrateCommand.add_arguments(self, parser)

    def handle(self, *args, **options):
        runschema = NonInteractiveRunSchemaCommand()
        options.pop("run_syncdb", False)
        if "skip_checks" not in options:
            options["skip_checks"] = True
        runschema.execute(command_name="django.core.migrate", *args, **options)


Command = MigrateSchemaCommand
