from django.conf import settings
from django.urls import reverse

from django_pgschemas.management.commands import TenantCommand
from django_pgschemas.routing.urlresolvers import get_urlconf_from_schema


class Command(TenantCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            dest="url_name",
            help="Url name to resolve in the specified schema",
        )

    def handle_tenant(self, tenant, *args, **options):
        if tenant.is_dynamic:
            primary_domain = tenant.get_primary_domain()
            tenant.domain_url = primary_domain.domain
            tenant.folder = primary_domain.folder
        else:
            tenant.domain_url = settings.TENANTS[tenant.schema_name]["DOMAINS"][0]
        self.stdout.write(reverse(options["url_name"], urlconf=get_urlconf_from_schema(tenant)))
