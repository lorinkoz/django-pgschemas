from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .utils import get_tenant_model


class DjangoPGSchemasConfig(AppConfig):
    name = "django_pgschemas"
    verbose_name = "Django Postgres Schemas"

    example_config = """
    TENANTS = {
        'public': {
            'APPS': ['django.contrib.contenttypes', 'core'],
            'TENANT_MODEL': 'core.Tenant',
            'DOMAIN_MODEL': 'core.Domain',
        },
        'www': {
            'APPS': ['www'],
            'URLCONF': 'www.urls',
            'DOMAINS': ['mydomain.com', 'www.mydomain.com'],
        },
        'help': {
            'APPS': ['help'],
            'URLCONF': 'help.urls',
            'DOMAINS': ['help.mydomain.com'],
        },
        'default': {
            'APPS': ['tenants'],
            'URLCONF': 'tenants.urls',
        }
    }
    """

    def ready(self):
        from django.db import connection

        if not isinstance(getattr(settings, "TENANTS", None), dict):
            raise ImproperlyConfigured("TENANTS dict setting not set.")

        # Public schema
        if not isinstance(settings.TENANTS.get("public"), dict):
            raise ImproperlyConfigured("TENANTS must contain a 'public' dict.")
        if "URLCONF" in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'URLCONF' key.")

        # Default schemas
        if not isinstance(settings.TENANTS.get("default"), dict):
            raise ImproperlyConfigured("TENANTS must contain a 'default' dict.")
        if "URLCONF" not in settings.TENANTS["default"]:
            raise ImproperlyConfigured("TENANTS['default'] must contain a 'URLCONF' key.")
        if "TENANT_MODEL" not in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['default'] must contain a 'TENANT_MODEL' key.")
        if "DOMAIN_MODEL" not in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['default'] must contain a 'DOMAIN_MODEL' key.")
        if "DOMAINS" in settings.TENANTS["default"]:
            raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'DOMAINS' key.")
        if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
            raise ImproperlyConfigured("'django.contrib.contenttypes' must be on 'public' schema.")

        # Custom schemas
        for schema in settings.TENANTS:
            if schema in ["public", "default"]:
                continue
            if not isinstance(settings.TENANTS[schema].get("DOMAINS"), list):
                raise ImproperlyConfigured("TENANTS['%s'] must contain a 'DOMAINS' list." % schema)
            if "django.contrib.contenttypes" in settings.TENANTS[schema].get("APPS", []):
                raise ImproperlyConfigured("'django.contrib.contenttypes' must be on 'public' schema.")

        # Other checks
        if "django_pgschemas.routers.SyncRouter" not in settings.DATABASE_ROUTERS:
            raise ImproperlyConfigured("DATABASE_ROUTERS setting must contain 'django_pgschemas.routers.SyncRouter'.")
        if settings.ROOT_URLCONF != settings.TENANTS["default"]["URLCONF"]:
            raise ImproperlyConfigured("ROOT_URLCONF must be equal to TENANTS['default']['URLCONF'] for consistency")

        # Consistency of PGSCHEMAS_EXTRA_SEARCH_PATHS
        if hasattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS"):
            if "public" in settings.PGSCHEMAS_EXTRA_SEARCH_PATHS:
                raise ImproperlyConfigured("'public' cannot be included on PGSCHEMAS_EXTRA_SEARCH_PATHS.")
            if "default" in settings.PGSCHEMAS_EXTRA_SEARCH_PATHS:
                raise ImproperlyConfigured("'default' cannot be included on PGSCHEMAS_EXTRA_SEARCH_PATHS.")
            TenantModel = get_tenant_model()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s;", [TenantModel._meta.db_table]
            )
            if cursor.fetchone():
                invalid_schemas = set(settings.PGSCHEMAS_EXTRA_SEARCH_PATHS).intersection(
                    TenantModel.objects.all().values_list("schema_name", flat=True)
                )
                if invalid_schemas:
                    raise ImproperlyConfigured(
                        "Do not include schemas (%s) on PGSCHEMAS_EXTRA_SEARCH_PATHS." % list(invalid_schemas)
                    )
