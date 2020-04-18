from io import StringIO

from django.core import management
from django.core.management.base import CommandError
from django.test import TransactionTestCase

from django_pgschemas.utils import get_tenant_model, get_domain_model


class WhoWillCommandTestCase(TransactionTestCase):
    """
    Tests the whowill management command.
    """

    @classmethod
    def setUpClass(cls):
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.test.com", is_primary=True)

    @classmethod
    def tearDownClass(cls):
        TenantModel = get_tenant_model()
        TenantModel.objects.all().delete()

    def split_output(self, buffer):
        buffer.seek(0)
        return set(buffer.read().strip().splitlines())

    def test_all_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", all_schemas=True, stdout=buffer)
            self.assertEqual(
                self.split_output(buffer), {"public", "sample", "test.com", "blog.test.com", "tenant1.test.com"}
            )

    def test_static_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", static_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"public", "sample", "test.com", "blog.test.com"})

    def test_tenant_like_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", tenant_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"sample", "tenant1.test.com"})

    def test_dynamic_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", dynamic_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"tenant1.test.com"})

    def test_specific_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", schemas=["www", "blog", "tenant1"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"test.com", "blog.test.com", "tenant1.test.com"})

    # Same test cases as before, but excluding one

    def test_all_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", all_schemas=True, excluded_schemas=["blog"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"public", "sample", "test.com", "tenant1.test.com"})

    def test_static_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", static_schemas=True, excluded_schemas=["sample"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"public", "test.com", "blog.test.com"})

    def test_tenant_like_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", tenant_schemas=True, excluded_schemas=["tenant1"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"sample"})

    def test_dynamic_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", dynamic_schemas=True, excluded_schemas=["public"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"tenant1.test.com"})

    def test_specific_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command(
                "whowill", schemas=["www", "blog", "tenant1"], excluded_schemas=["test"], stdout=buffer
            )
            self.assertEqual(self.split_output(buffer), {"blog.test.com", "tenant1.test.com"})
