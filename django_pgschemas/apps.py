from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import connection

from .utils import get_tenant_model, is_valid_schema_name


class DjangoPGSchemasConfig(AppConfig):
    name = "django_pgschemas"
    verbose_name = "Django PostgreSQL Schemas"

    def ready(self):
        user_app = get_user_model()._meta.app_config.name

        if not isinstance(getattr(settings, "TENANTS", None), dict):
            raise ImproperlyConfigured("TENANTS dict setting not set.")

        # Public schema
        if not isinstance(settings.TENANTS.get("public"), dict):
            raise ImproperlyConfigured("TENANTS must contain a 'public' dict.")
        if "URLCONF" in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'URLCONF' key.")
        if "WS_URLCONF" in settings.TENANTS["public"]:
            raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'WS_URLCONF' key.")

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
        if (
            "CLONE_REFERENCE" in settings.TENANTS["default"]
            and settings.TENANTS["default"]["CLONE_REFERENCE"] in settings.TENANTS
        ):
            raise ImproperlyConfigured("TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name")
        if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
            raise ImproperlyConfigured("'django.contrib.contenttypes' must be on 'public' schema.")

        # Custom schemas
        for schema in settings.TENANTS:
            schema_apps = settings.TENANTS[schema].get("APPS", [])
            if ("django.contrib.sessions" in schema_apps and user_app not in schema_apps) or (
                user_app in schema_apps and "django.contrib.sessions" not in schema_apps
            ):
                raise ImproperlyConfigured(
                    "'django.contrib.sessions' must be on schemas that also have '%s'." % user_app
                )
            if schema not in ["public", "default"]:
                if not is_valid_schema_name(schema):
                    raise ImproperlyConfigured("'%s' is not a valid schema name." % schema)
                if not isinstance(settings.TENANTS[schema].get("DOMAINS"), list):
                    raise ImproperlyConfigured("TENANTS['%s'] must contain a 'DOMAINS' list." % schema)
                if "django.contrib.contenttypes" in schema_apps:
                    raise ImproperlyConfigured("'django.contrib.contenttypes' must be on 'public' schema.")

        # Other checks
        if "django_pgschemas.routers.SyncRouter" not in settings.DATABASE_ROUTERS:
            raise ImproperlyConfigured("DATABASE_ROUTERS setting must contain 'django_pgschemas.routers.SyncRouter'.")
        if settings.ROOT_URLCONF != settings.TENANTS["default"]["URLCONF"]:
            raise ImproperlyConfigured("ROOT_URLCONF must be equal to TENANTS['default']['URLCONF'] for consistency")

        # Consistency of PGSCHEMAS_EXTRA_SEARCH_PATHS
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
            invalid_schemas = set(settings.PGSCHEMAS_EXTRA_SEARCH_PATHS).intersection(
                set(settings.TENANTS.keys()).union(dynamic_tenants)
            )
            if invalid_schemas:
                raise ImproperlyConfigured(
                    "Do not include '%s' on PGSCHEMAS_EXTRA_SEARCH_PATHS." % ", ".join(invalid_schemas)
                )
