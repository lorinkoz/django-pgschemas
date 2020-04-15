from django.apps import AppConfig
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection

from .utils import get_tenant_model, is_valid_schema_name


class DjangoPGSchemasConfig(AppConfig):
    name = "django_pgschemas"
    verbose_name = "Django PostgreSQL Schemas"

    def _check_tenant_dict(self):
        if not isinstance(getattr(settings, "TENANTS", None), dict):
            raise ImproperlyConfigured("TENANTS dict setting not set.")

    def _check_public_schema(self):
        if not isinstance(settings.TENANTS.get("public"), dict):
            raise ImproperlyConfigured("TENANTS must contain a 'public' dict.")
        if "TENANT_MODEL" not in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] must contain a 'TENANT_MODEL' key.")
        if "DOMAIN_MODEL" not in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] must contain a 'DOMAIN_MODEL' key.")
        if "URLCONF" in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'URLCONF' key.")
        if "WS_URLCONF" in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'WS_URLCONF' key.")

    def _check_default_schemas(self):
        if not isinstance(settings.TENANTS.get("default"), dict):
            raise ImproperlyConfigured("TENANTS must contain a 'default' dict.")
        if "URLCONF" not in settings.TENANTS["default"]:
            raise ImproperlyConfigured("TENANTS['default'] must contain a 'URLCONF' key.")
        if "DOMAINS" in settings.TENANTS["default"]:
            raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'DOMAINS' key.")
        if (
            "CLONE_REFERENCE" in settings.TENANTS["default"]
            and settings.TENANTS["default"]["CLONE_REFERENCE"] in settings.TENANTS
        ):
            raise ImproperlyConfigured("TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name")

    def _check_overall_schemas(self):
        for schema in settings.TENANTS:
            if schema not in ["public", "default"]:
                if not is_valid_schema_name(schema):
                    raise ImproperlyConfigured("'%s' is not a valid schema name." % schema)
                if not isinstance(settings.TENANTS[schema].get("DOMAINS"), list):
                    raise ImproperlyConfigured("TENANTS['%s'] must contain a 'DOMAINS' list." % schema)

    def _check_complementary_settings(self):
        if "django_pgschemas.routers.SyncRouter" not in settings.DATABASE_ROUTERS:
            raise ImproperlyConfigured("DATABASE_ROUTERS setting must contain 'django_pgschemas.routers.SyncRouter'.")

    def _check_extra_search_paths(self):
        if hasattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS"):
            TenantModel = get_tenant_model()
            cursor = connection.cursor()
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s;", [TenantModel._meta.db_table]
            )
            dynamic_tenants = []
            if "CLONE_REFERENCE" in settings.TENANTS["default"]:
                dynamic_tenants.append(settings.TENANTS["default"]["CLONE_REFERENCE"])
            if cursor.fetchone():
                dynamic_tenants += list(TenantModel.objects.all().values_list("schema_name", flat=True))
            cursor.close()
            invalid_schemas = set(settings.PGSCHEMAS_EXTRA_SEARCH_PATHS).intersection(
                set(settings.TENANTS.keys()).union(dynamic_tenants)
            )
            if invalid_schemas:
                raise ImproperlyConfigured(
                    "Do not include '%s' on PGSCHEMAS_EXTRA_SEARCH_PATHS." % ", ".join(invalid_schemas)
                )

    def ready(self):
        from . import checks

        self._check_tenant_dict()
        self._check_public_schema()
        self._check_default_schemas()
        self._check_overall_schemas()
        self._check_complementary_settings()
        self._check_extra_search_paths()
