from . import TenantCommand


class Command(TenantCommand):
    help = "Displays which schemas would be used based on the passed schema selectors"

    def handle_schema(self, schema, *args, **options):
        if options["verbosity"] >= 1:
            self.stdout.write(str(schema.routing) if schema.routing else schema.schema_name)
