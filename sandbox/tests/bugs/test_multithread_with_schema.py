import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from django_pgschemas import Schema, get_current_schema

FIRST_SCHEMA = "first_schema"
SECOND_SCHEMA = "second_schema"


@pytest.mark.bug
def test_multithread_with_schema():
    def handle_schema():
        with Schema.create(schema_name=FIRST_SCHEMA):
            assert get_current_schema().schema_name == FIRST_SCHEMA

            with Schema.create(schema_name=SECOND_SCHEMA):
                assert get_current_schema().schema_name == SECOND_SCHEMA
                time.sleep(0.001)

            assert get_current_schema().schema_name == FIRST_SCHEMA

            return get_current_schema().schema_name

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(handle_schema) for _ in range(15)]
        results = [future.result() for future in futures]
        assert all(value == FIRST_SCHEMA for value in results)
