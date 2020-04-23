from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

settings_public = {"TENANT_MODEL": "shared_public.Tenant", "DOMAIN_MODEL": "shared_public.Domain"}
settings_default = {"URLCONF": ""}


class AppConfigTestCase(TestCase):
    """
    Tests TENANTS settings is properly defined.
    """

    def setUp(self):
        self.app_config = apps.get_app_config("django_pgschemas")

    @override_settings()
    def test_missing_tenants(self):
        del settings.TENANTS
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_tenant_dict()

    @override_settings(TENANTS=list)
    def test_wrong_type_tenants(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_tenant_dict()

    @override_settings(TENANTS={})
    def test_no_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": None})
    def test_wrong_type_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": 4})
    def test_other_type_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": {"DOMAIN_MODEL": ""}})
    def test_no_tenant_model_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": {"TENANT_MODEL": ""}})
    def test_no_domain_model_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": {**settings_public, "URLCONF": ""}})
    def test_urlconf_on_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": {**settings_public, "WS_URLCONF": ""}})
    def test_wsurlconf_on_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS={"public": {**settings_public, "DOMAINS": ""}})
    def test_domains_on_public(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_public_schema()

    @override_settings(TENANTS=settings_public)
    def test_no_default(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_default_schemas()

    @override_settings(TENANTS={"default": None})
    def test_wrong_type_default(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_default_schemas()

    @override_settings(TENANTS={"default": "wawa"})
    def test_other_type_default(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_default_schemas()

    @override_settings(TENANTS={"default": {}})
    def test_no_urlconf_default(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_default_schemas()

    @override_settings(TENANTS={"default": {**settings_default, "DOMAINS": ""}})
    def test_domains_on_default(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_default_schemas()

    def test_repeated_clone_reference(self):
        with override_settings(TENANTS={"public": {}, "default": {**settings_default, "CLONE_REFERENCE": "public"}}):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_default_schemas()
        with override_settings(TENANTS={"default": {**settings_default, "CLONE_REFERENCE": "default"}}):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_default_schemas()

    def test_valid_schema_name(self):
        with override_settings(TENANTS={"pg_whatever": {}}):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_overall_schemas()
        with override_settings(TENANTS={"&$&*": {}}):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_overall_schemas()

    @override_settings(TENANTS={"www": {}})
    def test_domains_on_others(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_overall_schemas()

    @override_settings(DATABASE_ROUTERS=())
    def test_database_routers(self):
        with self.assertRaises(ImproperlyConfigured):
            self.app_config._check_complementary_settings()

    def test_extra_search_paths(self):
        with override_settings(
            TENANTS={"public": settings_public, "default": {}, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["public"]
        ):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_extra_search_paths()
        with override_settings(
            TENANTS={"public": settings_public, "default": {}, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["default"]
        ):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_extra_search_paths()
        with override_settings(
            TENANTS={"public": settings_public, "default": {}, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["www"]
        ):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_extra_search_paths()
        with override_settings(
            TENANTS={"public": settings_public, "default": {"CLONE_REFERENCE": "sample"}, "www": {}},
            PGSCHEMAS_EXTRA_SEARCH_PATHS=["sample"],
        ):
            with self.assertRaises(ImproperlyConfigured):
                self.app_config._check_extra_search_paths()

    @override_settings(TENANTS={"public": settings_public, "default": settings_default})
    def test_all_good_here(self):
        self.app_config.ready()
