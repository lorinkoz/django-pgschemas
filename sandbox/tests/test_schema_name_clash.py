import pytest
from django.core.exceptions import ValidationError


def test_tenant_save_rejects_static_schema_clash(TenantModel, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    tenant = TenantModel(schema_name="www")

    with pytest.raises(ValidationError, match="clashes"):
        tenant.save(verbosity=0)


def test_tenant_save_rejects_clone_reference_clash(TenantModel, tenants_settings, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    clone_reference = tenants_settings["default"].get("CLONE_REFERENCE")
    if not clone_reference:
        pytest.skip("Clone reference is not configured")

    tenant = TenantModel(schema_name=clone_reference)

    with pytest.raises(ValidationError, match="clashes"):
        tenant.save(verbosity=0)
