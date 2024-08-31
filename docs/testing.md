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
        tenant = Tenant.objects.get_or_create(schema_name="tenant1")
        Domain.objects.get_or_create(
            tenant=tenant,
            domain="tenant1.mydomain.com",
            is_primary=True,
        )
```

And also provide them as fixtures:

```python title="confest.py"
@pytest.fixture
def tenant(db):
    return Tenant.objects.get(schema_name="tenant1")
```

If you want the tenant to be activated automatically in your test cases, you can so as follows. Using the tenants as context manager is useful in activating the tenant only in the scope of each test.

```python title="confest.py"
@pytest.fixture
def tenant(db):
    with (tenant := Tenant.objects.get(schema_name="tenant1")):
        yield tenant
```

You can also define a fixture for a client, including the necessary headers:

```python title="confest.py"
from django.test import Client

@pytest.fixture
def domain_client():
    return Client(headers={"host": "tenant1.mydomain.com"})

@pytest.fixture
def header_client():
    return Client(headers={"tenant": "tenant1"})
```

## Django test cases

This package does not provide base clases to be used in place for Django's `TestCase`. If you need support in this regard, please visit the [dicussions section](https://github.com/lorinkoz/django-pgschemas/discussions) in the package's repository.
