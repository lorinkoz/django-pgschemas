from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import InternalError
from django.test import TestCase, override_settings

from django_pgschemas import utils, schema


class UtilsTestCase(TestCase):
    """
    Tests utility functions.
    """

    valid_identifiers = ["___", "a_a0", "_a0_", "a" * 63]
    invalid_identifiers = ["", " ", "^", ".", "&", "{", "(", "@", "!", "a" * 64]
    valid_schema_names = ["a_pg", "w_pg_a", "_pg_awa", "pgwa"] + valid_identifiers
    invalid_schema_names = ["pg_a", "pg_"] + invalid_identifiers

    def test_get_tenant_model(self):
        self.assertEqual(utils.get_tenant_model()._meta.model_name, "tenant")

    def test_get_domain_model(self):
        self.assertEqual(utils.get_domain_model()._meta.model_name, "domain")

    def test_get_tenant_database_alias(self):
        self.assertEqual(utils.get_tenant_database_alias(), "default")
        with override_settings(PGSCHEMAS_TENANT_DB_ALIAS="something"):
            self.assertEqual(utils.get_tenant_database_alias(), "something")

    def test_get_limit_set_calls(self):
        self.assertFalse(utils.get_limit_set_calls())
        with override_settings(PGSCHEMAS_LIMIT_SET_CALLS=True):
            self.assertTrue(utils.get_limit_set_calls())

    def test_get_clone_reference(self):
        self.assertEqual(utils.get_clone_reference(), "sample")
        with override_settings(TENANTS={"public": {}, "default": {}}):
            self.assertEqual(utils.get_clone_reference(), None)

    def test_is_valid_identifier(self):
        for identifier in self.valid_identifiers:
            self.assertTrue(utils.is_valid_identifier(identifier))
        for identifier in self.invalid_identifiers:
            self.assertFalse(utils.is_valid_identifier(identifier))

    def test_is_valid_schema_name(self):
        for schema_name in self.valid_schema_names:
            self.assertTrue(utils.is_valid_schema_name(schema_name))
        for schema_name in self.invalid_schema_names:
            self.assertFalse(utils.is_valid_schema_name(schema_name))

    def test_check_schema_name(self):
        for schema_name in self.valid_schema_names:
            utils.check_schema_name(schema_name)
        for schema_name in self.invalid_schema_names:
            with self.assertRaises(ValidationError):
                utils.check_schema_name(schema_name)

    def test_remove_www(self):
        self.assertEqual(utils.remove_www("test.com"), "test.com")
        self.assertEqual(utils.remove_www("www.test.com"), "test.com")
        self.assertEqual(utils.remove_www("wwwtest.com"), "wwwtest.com")
        self.assertEqual(utils.remove_www("www."), "")

    def test_run_in_public_schema(self):
        @utils.run_in_public_schema
        def inner():
            cursor = connection.cursor()
            cursor.execute("SHOW search_path")
            self.assertEqual(cursor.fetchone(), ("public",))
            cursor.close()

        with schema.SchemaDescriptor.create(schema_name="test"):
            inner()
            cursor = connection.cursor()
            cursor.execute("SHOW search_path")
            self.assertEqual(cursor.fetchone(), ("test, public",))
            cursor.close()

    def test_schema_exists(self):
        self.assertTrue(utils.schema_exists("public"))
        self.assertTrue(utils.schema_exists("www"))
        self.assertTrue(utils.schema_exists("blog"))
        self.assertTrue(utils.schema_exists("sample"))
        self.assertFalse(utils.schema_exists("default"))
        self.assertFalse(utils.schema_exists("tenant"))

    def test_dynamic_models_exist(self):
        self.assertTrue(utils.dynamic_models_exist())
        utils.drop_schema("public")
        self.assertFalse(utils.dynamic_models_exist())

    def test_create_drop_schema(self):
        self.assertFalse(utils.create_schema("public", check_if_exists=True))  # Schema existed already
        self.assertTrue(utils.schema_exists("public"))  # Schema exists
        self.assertTrue(utils.drop_schema("public"))  # Schema was dropped
        self.assertFalse(utils.drop_schema("public"))  # Schema no longer exists
        self.assertFalse(utils.schema_exists("public"))  # Schema doesn't exist
        self.assertTrue(utils.create_schema("public", sync_schema=False))  # Schema was created
        self.assertTrue(utils.schema_exists("public"))  # Schema exists

    def test_clone_schema(self):
        with schema.SchemaDescriptor.create(schema_name="public"):
            utils._create_clone_schema_function()
        self.assertFalse(utils.schema_exists("sample2"))  # Schema doesn't exist previously
        utils.clone_schema("sample", "sample2", dry_run=True)  # Dry run
        self.assertFalse(utils.schema_exists("sample2"))  # Schema won't exist, dry run
        utils.clone_schema("sample", "sample2")  # Real run, schema was cloned
        self.assertTrue(utils.schema_exists("sample2"))  # Schema exists
        with self.assertRaises(InternalError):
            utils.clone_schema("sample", "sample2")  # Schema already exists, error
        self.assertTrue(utils.schema_exists("sample2"))  # Schema still exists

    def test_create_or_clone_schema(self):
        self.assertFalse(utils.create_or_clone_schema("sample"))  # Schema existed
