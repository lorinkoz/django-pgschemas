from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.db.utils import ProgrammingError
from django.utils.module_loading import import_module

from .utils import get_clone_reference, get_domain_model, get_tenant_model


def get_tenant_app():
    return get_tenant_model(require_ready=False)._meta.app_config.name


def get_domain_app():
    return get_domain_model(require_ready=False)._meta.app_config.name


def get_user_app():
    try:
        return get_user_model()._meta.app_config.name
    except ImproperlyConfigured:
        return None


def get_session_app():
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore
    if hasattr(store, "get_model_class"):
        session_model = store.get_model_class()
        if issubclass(session_model, AbstractBaseSession):
            return session_model._meta.app_config.name
    return None


@checks.register()
def check_principal_apps(app_configs, **kwargs):
    errors = []
    tenant_app = get_tenant_app()
    domain_app = get_domain_app()
    if tenant_app not in settings.TENANTS["public"].get("APPS", []):
        errors.append(
            checks.Error("Your tenant app '%s' must be on the 'public' schema." % tenant_app, id="pgschemas.W001")
        )
    if domain_app not in settings.TENANTS["public"].get("APPS", []):
        errors.append(
            checks.Error("Your domain app '%s' must be on the 'public' schema." % domain_app, id="pgschemas.W001")
        )
    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema == "public":
            continue
        if tenant_app in schema_apps:
            errors.append(
                checks.Error(
                    "Your tenant app '%s' in TENANTS['%s']['APPS'] must be on the 'public' schema only."
                    % (tenant_app, schema),
                    id="pgschemas.W001",
                )
            )
        if domain_app in schema_apps:
            errors.append(
                checks.Error(
                    "Your domain app '%s' in TENANTS['%s']['APPS'] must be on the 'public' schema only."
                    % (domain_app, schema),
                    id="pgschemas.W001",
                )
            )
    return errors


@checks.register()
def check_other_apps(app_configs, **kwargs):
    errors = []
    user_app = get_user_app()
    session_app = get_session_app()
    if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
        errors.append(
            checks.Warning(
                "'django.contrib.contenttypes' in TENANTS['default']['APPS'] must be on 'public' schema only.",
                id="pgschemas.W002",
            )
        )
    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema not in ["public", "default"]:
            if "django.contrib.contenttypes" in schema_apps:
                errors.append(
                    checks.Warning(
                        "'django.contrib.contenttypes' in TENANTS['%s']['APPS'] must be on 'public' schema only."
                        % schema,
                        id="pgschemas.W002",
                    )
                )
        if user_app and session_app:
            if session_app in schema_apps and user_app not in schema_apps:
                errors.append(
                    checks.Warning(
                        "'%s' must be together with '%s' in TENANTS['%s']['APPS']." % (user_app, session_app, schema),
                        id="pgschemas.W003",
                    )
                )
            elif user_app in schema_apps and session_app not in schema_apps and session_app in settings.INSTALLED_APPS:
                errors.append(
                    checks.Warning(
                        "'%s' must be together with '%s' in TENANTS['%s']['APPS']." % (session_app, user_app, schema),
                        id="pgschemas.W003",
                    )
                )
    return errors


@checks.register(checks.Tags.database)
def check_schema_names(app_configs, **kwargs):
    errors = []
    static_names = set(settings.TENANTS.keys())
    clone_reference = get_clone_reference()
    if clone_reference:
        static_names.add(clone_reference)
    try:
        dynamic_names = set(get_tenant_model().objects.values_list("schema_name", flat=True))
    except ProgrammingError:
        # This happens on the first run of migrate, with empty database.
        # It can also happen when the tenant model contains unapplied migrations that break.
        dynamic_names = set()
    intersection = static_names & dynamic_names
    if intersection:
        errors.append(
            checks.Critical(
                "Name clash found between static and dynamic tenants: %s" % intersection,
                id="pgschemas.W004",
            )
        )
    return errors
