from django.conf import settings
from django.urls import reverse

from django_pgschemas.management.commands import TenantCommand
from django_pgschemas.routing.models import get_primary_domain_for_tenant
from django_pgschemas.routing.urlresolvers import get_urlconf_from_schema


class Command(TenantCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            dest="url_name",
            help="Url name to resolve in the specified schema",
        )

    def handle_schema(self, schema, *args, **options):
        if schema.is_dynamic:
            primary_domain = get_primary_domain_for_tenant(schema)
            schema.domain_url = primary_domain.domain
            schema.folder = primary_domain.folder
        else:
            schema.domain_url = settings.TENANTS[schema.schema_name]["DOMAINS"][0]
        self.stdout.write(reverse(options["url_name"], urlconf=get_urlconf_from_schema(schema)))
