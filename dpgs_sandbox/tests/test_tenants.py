from django.dispatch import receiver
from django.test import TransactionTestCase

from django_pgschemas.signals import schema_post_sync
from django_pgschemas.utils import get_tenant_model, schema_exists

TenantModel = get_tenant_model()


class TenantAutomaticTestCase(TransactionTestCase):
    """
    Tests tenant automatic operations.
    """

    def test_new_creation_deletion(self):
        "Tests automatic creation/deletion for new tenant's save/delete"
        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = True
        tenant.save(verbosity=0)
        self.assertTrue(schema_exists("tenant1"))
        tenant.auto_drop_schema = True
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertFalse(schema_exists("tenant1"))

    def test_existing_creation(self):
        "Tests automatic creation for existing tenant's save"
        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        tenant.auto_create_schema = True
        tenant.save(verbosity=0)
        self.assertTrue(schema_exists("tenant1"))
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertFalse(schema_exists("tenant1"))

    def test_new_aborted_creation(self):
        "Tests recovery on automatic creation for new tenant's save"

        def signal_receiver(*args, **kwargs):
            raise Exception

        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = True
        schema_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(0, TenantModel.objects.count())
        schema_post_sync.disconnect(signal_receiver)

    def test_existing_aborted_creation(self):
        "Tests recovery on automatic creation for new tenant's save"

        def signal_receiver(*args, **kwargs):
            raise Exception

        self.assertFalse(schema_exists("tenant1"))
        tenant = TenantModel(schema_name="tenant1")
        tenant.auto_create_schema = False
        tenant.save(verbosity=0)
        tenant.auto_create_schema = True
        schema_post_sync.connect(signal_receiver)
        with self.assertRaises(Exception):
            tenant.save(verbosity=0)
        self.assertFalse(schema_exists("tenant1"))
        self.assertEqual(1, TenantModel.objects.count())
        schema_post_sync.disconnect(signal_receiver)
        # Self-cleanup
        tenant.delete(force_drop=True)
        self.assertEqual(0, TenantModel.objects.count())
