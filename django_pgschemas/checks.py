from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import ProgrammingError
from django.utils.module_loading import import_module

from django_pgschemas.utils import get_clone_reference, get_tenant_model


def get_tenant_app() -> str | None:
    return settings.TENANTS["default"].get("TENANT_MODEL")


def get_domain_app() -> str | None:
    return settings.TENANTS["default"].get("DOMAIN_MODEL")


def get_user_app() -> str | None:
    try:
        return get_user_model()._meta.app_config.name
    except ImproperlyConfigured:
        return None


def get_session_app() -> str | None:
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore
    if hasattr(store, "get_model_class"):
        session_model = store.get_model_class()
        if issubclass(session_model, AbstractBaseSession):
            return session_model._meta.app_config.name
    return None


def ensure_tenant_dict():
    if not isinstance(getattr(settings, "TENANTS", None), dict):
        raise ImproperlyConfigured("TENANTS dict setting not set.")


def ensure_public_schema():
    if not isinstance(settings.TENANTS.get("public"), dict):
        raise ImproperlyConfigured("TENANTS must contain a 'public' dict.")

    public_tenant = settings.TENANTS["public"]

    if "URLCONF" in public_tenant:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'URLCONF' key.")
    if "WS_URLCONF" in public_tenant:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'WS_URLCONF' key.")
    if "DOMAINS" in public_tenant:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'DOMAINS' key.")
    if "FALLBACK_DOMAINS" in public_tenant:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'FALLBACK_DOMAINS' key.")


def ensure_default_schemas():
    if "default" not in settings.TENANTS:
        return  # Escape hatch for static only configs

    if not isinstance(settings.TENANTS["default"], dict):
        raise ImproperlyConfigured("TENANTS must contain a 'default' dict.")

    default_tenant = settings.TENANTS["default"]

    if "TENANT_MODEL" not in default_tenant:
        raise ImproperlyConfigured("TENANTS['default'] must contain a 'TENANT_MODEL' key.")
    if "URLCONF" not in default_tenant:
        raise ImproperlyConfigured("TENANTS['default'] must contain a 'URLCONF' key.")
    if "DOMAINS" in default_tenant:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'DOMAINS' key.")
    if "FALLBACK_DOMAINS" in default_tenant:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'FALLBACK_DOMAINS' key.")
    if default_tenant.get("CLONE_REFERENCE") in settings.TENANTS:
        raise ImproperlyConfigured(
            "TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name."
        )


def ensure_overall_schemas():
    from django_pgschemas.utils import is_valid_schema_name

    for schema in settings.TENANTS:
        if schema not in ["public", "default"]:
            if not is_valid_schema_name(schema):
                raise ImproperlyConfigured(f"'{schema}' is not a valid schema name.")


def ensure_extra_search_paths():
    from django_pgschemas.utils import get_tenant_model

    if hasattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS"):
        TenantModel = get_tenant_model()
        if TenantModel is None:
            return

        cursor = connection.cursor()
        cursor.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name = %s;",
            [TenantModel._meta.db_table],
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
            invalid = ", ".join(invalid_schemas)
            raise ImproperlyConfigured(
                f"Do not include '{invalid}' on PGSCHEMAS_EXTRA_SEARCH_PATHS."
            )


@checks.register()
def check_principal_apps(app_configs: Any, **kwargs: Any) -> None:
    errors = []
    tenant_app = get_tenant_app()
    domain_app = get_domain_app()

    if tenant_app is not None and tenant_app not in settings.TENANTS["public"].get("APPS", []):
        errors.append(
            checks.Error(
                f"Your tenant app '{tenant_app}' must be on the 'public' schema.",
                id="pgschemas.W001",
            )
        )
    if domain_app is not None and domain_app not in settings.TENANTS["public"].get("APPS", []):
        errors.append(
            checks.Error(
                f"Your domain app '{domain_app}' must be on the 'public' schema.",
                id="pgschemas.W001",
            )
        )

    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema == "public":
            continue
        if tenant_app is not None and tenant_app in schema_apps:
            errors.append(
                checks.Error(
                    "Your tenant app '{tenant_app}' in TENANTS['{schema}']['APPS'] "
                    "must be on the 'public' schema only.",
                    id="pgschemas.W001",
                )
            )
        if domain_app is not None and domain_app in schema_apps:
            errors.append(
                checks.Error(
                    "Your domain app '{domain_app}' in TENANTS['{schema}']['APPS'] "
                    "must be on the 'public' schema only.",
                    id="pgschemas.W001",
                )
            )

    return errors


@checks.register()
def check_other_apps(app_configs: Any, **kwargs: Any) -> None:
    errors = []
    user_app = get_user_app()
    session_app = get_session_app()

    if "django.contrib.contenttypes" in settings.TENANTS.get("default", {}).get("APPS", []):
        errors.append(
            checks.Warning(
                "'django.contrib.contenttypes' in TENANTS['default']['APPS'] "
                "must be on 'public' schema only.",
                id="pgschemas.W002",
            )
        )

    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema not in ["public", "default"]:
            if "django.contrib.contenttypes" in schema_apps:
                errors.append(
                    checks.Warning(
                        f"'django.contrib.contenttypes' in TENANTS['{schema}']['APPS'] "
                        "must be on 'public' schema only.",
                        id="pgschemas.W002",
                    )
                )
        if user_app and session_app:
            if session_app in schema_apps and user_app not in schema_apps:
                errors.append(
                    checks.Warning(
                        f"'{user_app}' must be together with '{session_app}' in "
                        f"TENANTS['{schema}']['APPS'].",
                        id="pgschemas.W003",
                    )
                )
            elif (
                user_app in schema_apps
                and session_app not in schema_apps
                and session_app in settings.INSTALLED_APPS
            ):
                errors.append(
                    checks.Warning(
                        f"'{session_app}' must be together with '{user_app}' in "
                        f"TENANTS['{schema}']['APPS'].",
                        id="pgschemas.W003",
                    )
                )

    return errors


@checks.register(checks.Tags.database)
def check_schema_names(app_configs: Any, **kwargs: Any) -> None:
    errors = []
    static_names = set(settings.TENANTS.keys())
    clone_reference = get_clone_reference()
    TenantModel = get_tenant_model()

    if TenantModel is None:
        return []

    if clone_reference:
        static_names.add(clone_reference)
    try:
        dynamic_names = set(TenantModel.objects.values_list("schema_name", flat=True))
    except ProgrammingError:
        # This happens on the first run of migrate, with empty database.
        # It can also happen when the tenant model contains unapplied migrations that break.
        dynamic_names = set()

    intersection = static_names & dynamic_names

    if intersection:
        errors.append(
            checks.Critical(
                f"Name clash found between static and dynamic tenants: {intersection}",
                id="pgschemas.W004",
            )
        )

    return errors
