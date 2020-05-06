from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

BASE_DEFAULT = {"TENANT_MODEL": "shared_public.Tenant", "DOMAIN_MODEL": "shared_public.Domain", "URLCONF": ""}


class AppConfigTestCase(TestCase):
    """
    Tests TENANTS settings is properly defined.
    """

    def setUp(self):
        self.app_config = apps.get_app_config("django_pgschemas")

    @override_settings()
    def test_missing_tenants(self):
        del settings.TENANTS
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_tenant_dict()
        self.assertEqual(str(ctx.exception), "TENANTS dict setting not set.")

    @override_settings(TENANTS=list)
    def test_wrong_type_tenants(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_tenant_dict()
        self.assertEqual(str(ctx.exception), "TENANTS dict setting not set.")

    @override_settings(TENANTS={})
    def test_no_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'public' dict.")

    @override_settings(TENANTS={"public": None})
    def test_wrong_type_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'public' dict.")

    @override_settings(TENANTS={"public": 4})
    def test_other_type_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'public' dict.")

    @override_settings(TENANTS={"public": {"URLCONF": ""}})
    def test_urlconf_on_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS['public'] cannot contain a 'URLCONF' key.")

    @override_settings(TENANTS={"public": {"WS_URLCONF": ""}})
    def test_wsurlconf_on_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS['public'] cannot contain a 'WS_URLCONF' key.")

    @override_settings(TENANTS={"public": {"DOMAINS": ""}})
    def test_domains_on_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS['public'] cannot contain a 'DOMAINS' key.")

    @override_settings(TENANTS={"public": {"FALLBACK_DOMAINS": ""}})
    def test_fallback_domains_on_public(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_public_schema()
        self.assertEqual(str(ctx.exception), "TENANTS['public'] cannot contain a 'FALLBACK_DOMAINS' key.")

    @override_settings(TENANTS={})
    def test_no_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'default' dict.")

    @override_settings(TENANTS={"default": None})
    def test_wrong_type_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'default' dict.")

    @override_settings(TENANTS={"default": "wawa"})
    def test_other_type_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS must contain a 'default' dict.")

    @override_settings(TENANTS={"default": {"DOMAIN_MODEL": ""}})
    def test_no_tenant_model_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['default'] must contain a 'TENANT_MODEL' key.")

    @override_settings(TENANTS={"default": {"TENANT_MODEL": ""}})
    def test_no_domain_model_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['default'] must contain a 'DOMAIN_MODEL' key.")

    @override_settings(TENANTS={"default": {"TENANT_MODEL": None, "DOMAIN_MODEL": None}})
    def test_no_urlconf_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['default'] must contain a 'URLCONF' key.")

    @override_settings(TENANTS={"default": {**BASE_DEFAULT, "DOMAINS": ""}})
    def test_domains_on_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['default'] cannot contain a 'DOMAINS' key.")

    @override_settings(TENANTS={"default": {**BASE_DEFAULT, "FALLBACK_DOMAINS": ""}})
    def test_fallback_domains_on_default(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_default_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['default'] cannot contain a 'FALLBACK_DOMAINS' key.")

    def test_repeated_clone_reference(self):
        with override_settings(TENANTS={"public": {}, "default": {**BASE_DEFAULT, "CLONE_REFERENCE": "public"}}):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_default_schemas()
            self.assertEqual(str(ctx.exception), "TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name.")
        with override_settings(TENANTS={"default": {**BASE_DEFAULT, "CLONE_REFERENCE": "default"}}):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_default_schemas()
            self.assertEqual(str(ctx.exception), "TENANTS['default']['CLONE_REFERENCE'] must be a unique schema name.")

    def test_valid_schema_name(self):
        with override_settings(TENANTS={"pg_whatever": {}}):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_overall_schemas()
            self.assertEqual(str(ctx.exception), "'pg_whatever' is not a valid schema name.")
        with override_settings(TENANTS={"&$&*": {}}):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_overall_schemas()
            self.assertEqual(str(ctx.exception), "'&$&*' is not a valid schema name.")

    @override_settings(TENANTS={"www": {}})
    def test_domains_on_others(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_overall_schemas()
        self.assertEqual(str(ctx.exception), "TENANTS['www'] must contain a 'DOMAINS' list.")

    @override_settings(DATABASE_ROUTERS=())
    def test_database_routers(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            self.app_config._check_complementary_settings()
        self.assertEqual(
            str(ctx.exception), "DATABASE_ROUTERS setting must contain 'django_pgschemas.routers.SyncRouter'."
        )

    def test_extra_search_paths(self):
        with override_settings(
            TENANTS={"public": {}, "default": BASE_DEFAULT, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["public"]
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_extra_search_paths()
            self.assertEqual(str(ctx.exception), "Do not include 'public' on PGSCHEMAS_EXTRA_SEARCH_PATHS.")
        with override_settings(
            TENANTS={"public": {}, "default": BASE_DEFAULT, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["default"]
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_extra_search_paths()
            self.assertEqual(str(ctx.exception), "Do not include 'default' on PGSCHEMAS_EXTRA_SEARCH_PATHS.")
        with override_settings(
            TENANTS={"public": {}, "default": BASE_DEFAULT, "www": {}}, PGSCHEMAS_EXTRA_SEARCH_PATHS=["www"]
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_extra_search_paths()
            self.assertEqual(str(ctx.exception), "Do not include 'www' on PGSCHEMAS_EXTRA_SEARCH_PATHS.")
        with override_settings(
            TENANTS={"public": {}, "default": {**BASE_DEFAULT, "CLONE_REFERENCE": "sample"}, "www": {}},
            PGSCHEMAS_EXTRA_SEARCH_PATHS=["sample"],
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self.app_config._check_extra_search_paths()
            self.assertEqual(str(ctx.exception), "Do not include 'sample' on PGSCHEMAS_EXTRA_SEARCH_PATHS.")

    @override_settings(TENANTS={"public": {}, "default": BASE_DEFAULT})
    def test_all_good_here(self):
        self.app_config.ready()
