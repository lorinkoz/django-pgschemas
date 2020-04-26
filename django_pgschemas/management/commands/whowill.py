from django.core import management
from django.core.management.base import BaseCommand

from . import TenantCommand


class Command(TenantCommand):
    help = "Displays which schemas would be used based on the passed schema selectors"

    def handle_tenant(self, tenant, *args, **options):
        if options["verbosity"] >= 1:
            self.stdout.write(str(tenant.get_primary_domain() or tenant.schema_name))
