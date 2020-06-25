from django.conf import settings
from django.core.checks import Tags, run_checks
from django.core.management.base import BaseCommand, CommandError

from ...utils import create_schema, drop_schema, get_clone_reference


class Command(BaseCommand):
    help = "Creates the reference schema for faster dynamic tenant creation"

    def _run_checks(self, **kwargs):
        issues = run_checks(tags=[Tags.database])
        issues.extend(super()._run_checks(**kwargs))
        return issues

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--recreate", action="store_true", dest="recreate", help="Recreate reference schema.")

    def handle(self, *args, **options):
        clone_reference = get_clone_reference()
        if not clone_reference:
            raise CommandError("There is no reference schema configured.")
        for database in settings.DATABASES:
            if options.get("recreate", False):
                drop_schema(clone_reference, database=database, check_if_exists=True, verbosity=options["verbosity"])
                if options["verbosity"] >= 1:
                    self.stdout.write(f"[{database}] Destroyed existing reference schema.")
            created = create_schema(
                clone_reference, database=database, check_if_exists=True, verbosity=options["verbosity"]
            )
            if options["verbosity"] >= 1:
                if created:
                    self.stdout.write(f"[{database}] Reference schema successfully created!")
                else:
                    self.stdout.write(f"[{database}] Reference schema already exists.")
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{database}] Run this command again with --recreate if you want to "
                            "recreate the reference schema."
                        )
                    )
