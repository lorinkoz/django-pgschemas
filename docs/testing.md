# Testing

This is how you set up dynamic tenants for testing.

## Pytest

You can define some tenants in the test configuration.

```python title="confest.py"
import pytest
from tenants.models import Tenant, Domain

@pytest.fixture(scope="session", autouse=True)
def setup(django_db_setup, django_db_blocker):

    with django_db_blocker.unblock():
        tenant = Tenant.objects.get_or_create(schema_name="test_tenant")
        Domain.objects.get_or_create(tenant=tenant, domain="test_tenant.mydomain.com", is_primary=True)
        Domain.objects.get_or_create(tenant=tenant, domain="tenants.mydomain.com", folder="test_tenant")
```

And also provide them as fixtures:

```python title="confest.py"
@pytest.fixture
def tenant():
    return Tenant.objects.get(schema_name="tenant1")
```
