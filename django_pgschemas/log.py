import logging

from django.db import connection


class SchemaContextFilter(logging.Filter):
    """
    Add the current ``schema_name`` and ``domain_url`` to log records.
    """

    def filter(self, record):
        record.schema_name = connection.schema.schema_name
        record.domain_url = connection.schema.domain_url
        return True
