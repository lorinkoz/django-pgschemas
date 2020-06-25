import logging

from .schema import schema_handler


class SchemaContextFilter(logging.Filter):
    """
    Add the current ``schema_name`` and ``domain_url`` to log records.
    """

    def filter(self, record):
        record.schema_name = schema_handler.active.schema_name
        record.domain_url = schema_handler.active.domain_url
        return True
