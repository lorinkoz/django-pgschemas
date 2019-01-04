from django.core.management.base import BaseCommand, CommandError

from ...utils import get_clone_sample, create_schema, drop_schema


class Command(BaseCommand):
    help = "Creates the sample schema for faster dynamic tenant creation"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--recreate", action="store_true", dest="recreate", help="Recreate sample schema.")

    def handle(self, *args, **options):
        clone_sample = get_clone_sample()
        if not clone_sample:
            raise CommandError("There is no sample schema configured.")
        if options.get("recreate", False):
            drop_schema(clone_sample, check_if_exists=True, verbosity=options["verbosity"])
            if options["verbosity"] >= 1:
                self.stdout.write("Destroyed existing sample.")
        created = create_schema(clone_sample, check_if_exists=True, verbosity=options["verbosity"])
        if options["verbosity"] >= 1:
            if created:
                self.stdout.write("Sample schema successfully created!")
            else:
                self.stdout.write("Sample schema already exists.")
                self.stdout.write(
                    self.style.WARNING(
                        "Run this command again with --recreate if you want to recreate the sample schema."
                    )
                )
