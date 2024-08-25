from . import TenantCommand


class Command(TenantCommand):
    help = "Displays which schemas would be used based on the passed schema selectors"

    def handle_tenant(self, tenant, *args, **options):
        if options["verbosity"] >= 1:
            self.stdout.write(str(tenant.routing) if tenant.routing else tenant.schema_name)
