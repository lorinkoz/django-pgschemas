from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.db.utils import ProgrammingError
from django.utils.module_loading import import_module

from django_pgschemas.settings import get_extra_search_paths
from django_pgschemas.utils import (
    get_clone_reference,
    get_domain_model,
    get_tenant_model,
    is_valid_schema_name,
)


def get_tenant_app() -> str | None:
    model = get_tenant_model()

    if model is None:
        return None

    return model._meta.app_config.name


def get_domain_app() -> str | None:
    model = get_domain_model()

    if model is None:
        return None

    return model._meta.app_config.name


def get_user_app() -> str | None:
    try:
        return get_user_model()._meta.app_config.name
    except (AttributeError, ImproperlyConfigured):
        return None


def get_session_app() -> str | None:
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore
    if hasattr(store, "get_model_class"):
        session_model = store.get_model_class()
        if issubclass(session_model, AbstractBaseSession):
            return session_model._meta.app_config.name
    return None


def ensure_tenant_dict() -> None:
    if not isinstance(getattr(settings, "TENANTS", None), dict):
        raise ImproperlyConfigured("TENANTS dict setting not set.")


def ensure_public_schema() -> None:
    if not isinstance(settings.TENANTS.get("public"), dict):
        raise ImproperlyConfigured("TENANTS must contain a 'public' dict.")

    tenants_public = settings.TENANTS["public"]

    if "URLCONF" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'URLCONF' key.")
    if "WS_URLCONF" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'WS_URLCONF' key.")
    if "DOMAINS" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'DOMAINS' key.")
    if "SESSION_KEY" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'SESSION_KEY' key.")
    if "HEADER" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'HEADER' key.")
    if "FALLBACK_DOMAINS" in tenants_public:
        raise ImproperlyConfigured("TENANTS['public'] cannot contain a 'FALLBACK_DOMAINS' key.")


def ensure_default_schemas() -> None:
    if "default" not in settings.TENANTS:
        return  # Escape hatch for static only configs

    if not isinstance(settings.TENANTS["default"], dict):
        raise ImproperlyConfigured("TENANTS must contain a 'default' dict.")

    tenants_default = settings.TENANTS["default"]

    if "TENANT_MODEL" not in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] must contain a 'TENANT_MODEL' key.")
    if "URLCONF" not in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] must contain a 'URLCONF' key.")
    if "DOMAINS" in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'DOMAINS' key.")
    if "SESSION_KEY" in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'SESSION_KEY' key.")
    if "HEADER" in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'HEADER' key.")
    if "FALLBACK_DOMAINS" in tenants_default:
        raise ImproperlyConfigured("TENANTS['default'] cannot contain a 'FALLBACK_DOMAINS' key.")
    if tenants_default.get("CLONE_REFERENCE") in settings.TENANTS:
        raise ImproperlyConfigured(
            "TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name."
        )


def ensure_overall_schemas() -> None:
    for schema in settings.TENANTS:
        if schema not in ["public", "default"]:
            if not is_valid_schema_name(schema):
                raise ImproperlyConfigured(f"'{schema}' is not a valid schema name.")


def ensure_extra_search_paths() -> None:
    if not (extra_search_paths := get_extra_search_paths()):
        return

    TenantModel = get_tenant_model()

    dynamic_tenants = []

    if "default" in settings.TENANTS and "CLONE_REFERENCE" in settings.TENANTS["default"]:
        dynamic_tenants.append(settings.TENANTS["default"]["CLONE_REFERENCE"])

    if TenantModel is not None:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = %s;",
                [TenantModel._meta.db_table],
            )
            if cursor.fetchone():
                dynamic_tenants += list(TenantModel.objects.values_list("schema_name", flat=True))

    invalid_schemas = set(extra_search_paths) & (
        set(settings.TENANTS.keys()) | set(dynamic_tenants)
    )

    if invalid_schemas:
        invalid = ", ".join(invalid_schemas)
        raise ImproperlyConfigured(f"Do not include '{invalid}' on PGSCHEMAS_EXTRA_SEARCH_PATHS.")


@checks.register()
def check_principal_apps(app_configs: Any, **kwargs: Any) -> list:
    errors = []
    tenant_app = get_tenant_app()
    domain_app = get_domain_app()

    tenants_public = settings.TENANTS["public"]

    if tenant_app is not None and tenant_app not in tenants_public.get("APPS", []):
        errors.append(
            checks.Error(
                f"Your tenant app '{tenant_app}' must be on the 'public' schema.",
                id="pgschemas.W001",
            )
        )
    if domain_app is not None and domain_app not in tenants_public.get("APPS", []):
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
                    f"Your tenant app '{tenant_app}' in TENANTS['{schema}']['APPS'] "
                    "must be on the 'public' schema only.",
                    id="pgschemas.W001",
                )
            )
        if domain_app is not None and domain_app in schema_apps:
            errors.append(
                checks.Error(
                    f"Your domain app '{domain_app}' in TENANTS['{schema}']['APPS'] "
                    "must be on the 'public' schema only.",
                    id="pgschemas.W001",
                )
            )

    return errors


@checks.register()
def check_other_apps(app_configs: Any, **kwargs: Any) -> list:
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
def check_schema_names(app_configs: Any, **kwargs: Any) -> list:
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
