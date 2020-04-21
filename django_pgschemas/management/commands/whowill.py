from django.core import management
from django.core.management.base import BaseCommand

from . import TenantCommand


class Command(TenantCommand):
    def handle_tenant(self, tenant, *args, **options):
        if options["verbosity"] >= 1:
            self.stdout.write(str(tenant.get_primary_domain() or tenant.schema_name))
