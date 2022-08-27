from django.apps import apps
from django.test import SimpleTestCase

from django_pgschemas.test.cases import StaticTenantTestCase
from django_pgschemas.utils import get_clone_reference

BlogEntry = apps.get_model("app_blog.BlogEntry")
User = apps.get_model("shared_common.User")


class TestSetUpStaticTenantTestCase(SimpleTestCase):
    """
    Tests the set up behavior of the StaticTenantTestCase.
    """

    def assert_expected_error(self, klass):
        with self.assertRaises(AssertionError) as ctx:
            klass.setUpClass()
        self.assertEqual(
            str(ctx.exception),
            f"{klass.__name__}.schema_name must be defined to a valid static tenant",
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

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(email="admin@localhost", display_name="Admin")
        BlogEntry.objects.create(user=cls.user)

    def test_correct_set_up(self):
        self.assertTrue(self.tenant)
        self.assertEqual(self.tenant.schema_name, "blog")
        self.assertEqual(self.tenant.domain_url, "blog.localhost")

    def test_random_operation1(self):
        BlogEntry.objects.create(user=self.user)
        BlogEntry.objects.create(user=self.user)
        self.assertEqual(BlogEntry.objects.count(), 3)

    def test_random_operation2(self):
        BlogEntry.objects.all().delete()
        self.assertEqual(BlogEntry.objects.count(), 0)

    def test_random_operation3(self):
        self.assertEqual(BlogEntry.objects.count(), 1)
