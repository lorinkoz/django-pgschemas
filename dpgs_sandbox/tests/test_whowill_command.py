from io import StringIO

from django.core import management
from django.test import TestCase

from django_pgschemas.utils import get_domain_model, get_tenant_model

TenantModel = get_tenant_model()
DomainModel = get_domain_model()


class WhoWillCommandTestCase(TestCase):
    """
    Tests the whowill management command.
    """

    @classmethod
    def setUpTestData(cls):
        TenantModel.objects.all().delete()  # Removing default dynamic tenant
        tenant = TenantModel(schema_name="tenant1")
        tenant.save(verbosity=0)
        DomainModel.objects.create(tenant=tenant, domain="tenant1.sandbox.com", is_primary=True)

    def split_output(self, buffer):
        buffer.seek(0)
        return set(buffer.read().strip().splitlines())

    def test_all_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", all_schemas=True, stdout=buffer)
            self.assertEqual(
                self.split_output(buffer),
                {
                    "public",
                    "sample",
                    "sandbox.com",
                    "blog.sandbox.com",
                    "tenant1.sandbox.com",
                },
            )

    def test_static_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", static_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"public", "sample", "sandbox.com", "blog.sandbox.com"})

    def test_tenant_like_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", tenant_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"sample", "tenant1.sandbox.com"})

    def test_dynamic_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", dynamic_schemas=True, stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"tenant1.sandbox.com"})

    def test_specific_schemas(self):
        with StringIO() as buffer:
            management.call_command("whowill", schemas=["www", "blog", "tenant1"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"sandbox.com", "blog.sandbox.com", "tenant1.sandbox.com"})

    # Same test cases as before, but excluding one

    def test_all_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", all_schemas=True, excluded_schemas=["blog"], stdout=buffer)
            self.assertEqual(
                self.split_output(buffer),
                {"public", "sample", "sandbox.com", "tenant1.sandbox.com"},
            )

    def test_static_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", static_schemas=True, excluded_schemas=["sample"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"public", "sandbox.com", "blog.sandbox.com"})

    def test_tenant_like_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", tenant_schemas=True, excluded_schemas=["tenant1"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"sample"})

    def test_dynamic_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command("whowill", dynamic_schemas=True, excluded_schemas=["public"], stdout=buffer)
            self.assertEqual(self.split_output(buffer), {"tenant1.sandbox.com"})

    def test_specific_schemas_minus_one(self):
        with StringIO() as buffer:
            management.call_command(
                "whowill", schemas=["www", "blog", "tenant1"], excluded_schemas=["sandbox.com"], stdout=buffer
            )
            self.assertEqual(self.split_output(buffer), {"blog.sandbox.com", "tenant1.sandbox.com"})
