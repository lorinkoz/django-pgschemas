from django.core.management.base import BaseCommand, CommandError

from ...utils import get_clone_reference, create_schema, drop_schema


class Command(BaseCommand):
    help = "Creates the reference schema for faster dynamic tenant creation"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--recreate", action="store_true", dest="recreate", help="Recreate reference schema.")

    def handle(self, *args, **options):
        clone_reference = get_clone_reference()
        if not clone_reference:
            raise CommandError("There is no reference schema configured.")
        if options.get("recreate", False):
            drop_schema(clone_reference, check_if_exists=True, verbosity=options["verbosity"])
            if options["verbosity"] >= 1:
                self.stdout.write("Destroyed existing reference schema.")
        created = create_schema(clone_reference, check_if_exists=True, verbosity=options["verbosity"])
        if options["verbosity"] >= 1:
            if created:
                self.stdout.write("Reference schema successfully created!")
            else:
                self.stdout.write("Reference schema already exists.")
                self.stdout.write(
                    self.style.WARNING(
                        "Run this command again with --recreate if you want to recreate the reference schema."
                    )
                )
