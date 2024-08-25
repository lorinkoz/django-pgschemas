from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from django_pgschemas import utils


@pytest.fixture(autouse=True)
def _setup(TenantModel):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")


def test_cloneschema(transactional_db):
    utils._create_clone_schema_function()

    assert not utils.schema_exists("cloned")

    call_command("cloneschema", "sample", "cloned", verbosity=0)  # All good

    assert utils.schema_exists("cloned")

    with pytest.raises(CommandError):  # Existing destination
        call_command("cloneschema", "sample", "cloned", verbosity=0)

    with pytest.raises(CommandError):  # Not existing source
        call_command("cloneschema", "nonexisting", "newschema", verbosity=0)

    utils.drop_schema("cloned")


def test_createrefschema(transactional_db):
    utils.drop_schema("cloned")
    call_command("createrefschema", verbosity=0)  # All good

    assert utils.schema_exists("sample")

    utils.drop_schema("cloned")
    call_command("createrefschema", recreate=True, verbosity=0)  # All good too

    assert utils.schema_exists("sample")

    utils.drop_schema("cloned")
    call_command("createrefschema", recreate=True, verbosity=0)  # All good too

    assert utils.schema_exists("sample")


def test_interactive_cloneschema(transactional_db):
    answer_provider = (
        n
        for n in [
            "y",  # Would you like to create a database entry?
            "",  # Domain name, simulated wrong answer
            "tenant1copy.localhost",  # Domain name, good answer
        ]
    )

    def patched_input(*args, **kwargs):
        return next(answer_provider)

    with patch("builtins.input", patched_input):
        call_command(
            "cloneschema",
            "tenant1",
            "tenant1copy",
            verbosity=0,
        )

    assert utils.schema_exists("tenant1copy")

    utils.drop_schema("tenant1copy")
