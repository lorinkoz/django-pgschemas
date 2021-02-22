from django.test import SimpleTestCase

from django_pgschemas.test.cases import StaticTenantTestCase
from django_pgschemas.utils import get_clone_reference


class TestSetUpStaticTenantTestCase(SimpleTestCase):
    """
    Tests the set up behavior of the StaticTenantTestCase.
    """

    def assert_expected_error(self, klass):
        with self.assertRaises(AssertionError) as ctx:
            klass.setUpClass()
        self.assertEqual(
            str(ctx.exception),
            "{class_name}.schema_name must be defined to a valid static tenant".format(class_name=klass.__name__),
        )

    def test_set_up_with_empty(self):
        class DummyStaticTenantTestCase(StaticTenantTestCase):
            pass

        self.assert_expected_error(DummyStaticTenantTestCase)

    def test_set_up_with_public(self):
        class DummyStaticTenantTestCase(StaticTenantTestCase):
            schema_name = "public"

        self.assert_expected_error(DummyStaticTenantTestCase)

    def test_set_up_with_default(self):
        class DummyStaticTenantTestCase(StaticTenantTestCase):
            schema_name = "default"

        self.assert_expected_error(DummyStaticTenantTestCase)

    def test_set_up_with_clone_reference(self):
        class DummyStaticTenantTestCase(StaticTenantTestCase):
            schema_name = get_clone_reference()

        self.assert_expected_error(DummyStaticTenantTestCase)

    def test_set_up_with_non_existing(self):
        class DummyStaticTenantTestCase(StaticTenantTestCase):
            schema_name = "nonstatictenant"

        self.assert_expected_error(DummyStaticTenantTestCase)


class TestStaticTenantTestCase(StaticTenantTestCase):
    """
    Tests the behavior of the StaticTenantTestCase.
    """

    schema_name = "blog"

    def test_correct_set_up(self):
        self.assertTrue(self.tenant)
        self.assertEqual(self.tenant.schema_name, "blog")
        self.assertEqual(self.tenant.domain_url, "blog.test.com")
