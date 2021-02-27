from channels.auth import AuthMiddleware, CookieMiddleware, SessionMiddleware, _get_user_session_key
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, load_backend
from django.contrib.auth.models import AnonymousUser
from django.utils.crypto import constant_time_compare


@database_sync_to_async
def get_user(scope):
    """
    Return the user model instance associated with the given scope.
    If no user is retrieved, return an instance of `AnonymousUser`.
    """
    if "session" not in scope:
        raise ValueError("Cannot find session in scope. You should wrap your consumer in SessionMiddleware.")
    user = None
    session = scope["session"]
    with scope["tenant"]:
        try:
            user_id = _get_user_session_key(session)
            backend_path = session[BACKEND_SESSION_KEY]
        except KeyError:
            pass
        else:
            if backend_path in settings.AUTHENTICATION_BACKENDS:
                backend = load_backend(backend_path)
                user = backend.get_user(user_id)
                # Verify the session
                if hasattr(user, "get_session_auth_hash"):
                    session_hash = session.get(HASH_SESSION_KEY)
                    session_hash_verified = session_hash and constant_time_compare(
                        session_hash, user.get_session_auth_hash()
                    )
                    if not session_hash_verified:
                        session.flush()
                        user = None
    return user or AnonymousUser()


class TenantAuthMiddleware(AuthMiddleware):
    async def resolve_scope(self, scope):
        scope["user"]._wrapped = await get_user(scope)


def TenantAuthMiddlewareStack(inner):
    return CookieMiddleware(SessionMiddleware(TenantAuthMiddleware(inner)))
