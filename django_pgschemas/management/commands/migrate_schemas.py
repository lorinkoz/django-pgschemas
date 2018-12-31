from django.core import management
from django.core.management.base import BaseCommand

from . import WrappedSchemaOption


class MigrateSchemasCommand(WrappedSchemaOption, BaseCommand):
    def handle(self, *args, **options):
        management.call_command("runschema", "django.core.migrate", *args, **options)


Command = MigrateSchemasCommand
