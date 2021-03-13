import logging

from .schema import get_current_schema


class SchemaContextFilter(logging.Filter):
    """
    Add the current ``schema_name`` and ``domain_url`` to log records.
    """

    def filter(self, record):
        current_schema = get_current_schema()
        record.schema_name = current_schema.schema_name
        record.domain_url = current_schema.domain_url
        return True
