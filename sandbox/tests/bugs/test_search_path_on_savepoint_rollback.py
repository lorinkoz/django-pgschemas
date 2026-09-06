import pytest
from django.db import connection, transaction

from django_pgschemas.schema import Schema, activate, deactivate, get_current_schema


class ControlledException(Exception):
    pass


def _create_savepoint():
    # Django 6.1 deprecated transaction.savepoint() in favor of savepoint_create().
    create = getattr(transaction, "savepoint_create", getattr(transaction, "savepoint"))
    return create()


@pytest.mark.bug
def test_search_path_reset_on_nested_atomic_rollback(settings, db):
    """
    Manual activate() inside a nested atomic leaves the schema selected after
    the inner block rolls back. SET search_path is transactional, so Postgres
    reverts it; with PGSCHEMAS_LIMIT_SET_CALLS the connection cache would skip
    re-SET and later queries would hit the outer schema.
    """
    settings.PGSCHEMAS_LIMIT_SET_CALLS = True
    deactivate()
    schema = Schema.create(schema_name="www")

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            assert cursor.fetchone() == ("public",)

        try:
            with transaction.atomic():
                activate(schema)
                with connection.cursor() as cursor:
                    cursor.execute("SHOW search_path")
                    assert cursor.fetchone() == ("www, public",)
                raise ControlledException()
        except ControlledException:
            pass

        assert get_current_schema().schema_name == "www"

        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            assert cursor.fetchone() == ("www, public",)


@pytest.mark.bug
def test_search_path_reset_on_explicit_savepoint_rollback(settings, db):
    settings.PGSCHEMAS_LIMIT_SET_CALLS = True
    deactivate()
    schema = Schema.create(schema_name="www")

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SHOW search_path")
            assert cursor.fetchone() == ("public",)

        sid = _create_savepoint()
        with schema:
            with connection.cursor() as cursor:
                cursor.execute("SHOW search_path")
                assert cursor.fetchone() == ("www, public",)

            transaction.savepoint_rollback(sid)

            assert connection._search_path is None

            with connection.cursor() as cursor:
                cursor.execute("SHOW search_path")
                assert cursor.fetchone() == ("www, public",)
