from . import TenantCommand


class Command(TenantCommand):
    help = "Displays which schemas would be used based on the passed schema selectors"

    def handle_tenant(self, tenant, *args, **options):
        if options["verbosity"] >= 1:
            self.stdout.write(
                str(tenant.get_primary_domain()) if tenant.is_dynamic else tenant.domain_url or tenant.schema_name
            )
