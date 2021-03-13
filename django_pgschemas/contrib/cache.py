from ..schema import get_current_schema


def make_key(key, key_prefix, version):
    """
    Tenant aware function to generate a cache key.

    Constructs the key used by all other methods. Prepends the tenant
    `schema_name` and `key_prefix'.
    """
    current_schema = get_current_schema()
    return "%s:%s:%s:%s" % (current_schema.schema_name, key_prefix, version, key)


def reverse_key(key):
    """
    Tenant aware function to reverse a cache key.

    Required for django-redis REVERSE_KEY_FUNCTION setting.
    """
    return key.split(":", 3)[3]
