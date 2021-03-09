from django_pgschemas.contrib.cache import make_key, reverse_key
from django_pgschemas.test.cases import FastTenantTestCase


class CacheHelperTestCase(FastTenantTestCase):
    def test_make_key(self):
        key = make_key(key="foo", key_prefix="", version=1)
        tenant_prefix = key.split(":")[0]
        self.assertEqual(self.tenant.schema_name, tenant_prefix)

    def test_reverse_key(self):
        key = "foo"
        self.assertEqual(key, reverse_key(make_key(key=key, key_prefix="", version=1)))
