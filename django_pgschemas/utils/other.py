def remove_www(hostname: str) -> str:
    """
    Removes ``www``. from the beginning of the address. Only for
    routing purposes. ``www.test.com/login/`` and ``test.com/login/`` should
    find the same tenant.
    """
    if hostname.startswith("www."):
        return hostname[4:]
    return hostname


def django_is_in_test_mode() -> bool:
    """
    I know this is very ugly! I'm looking for more elegant solutions.
    See: http://stackoverflow.com/questions/6957016/detect-django-testing-mode
    """
    from django.core import mail

    return hasattr(mail, "outbox")
