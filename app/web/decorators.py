from functools import wraps
from aiohttp_session import get_session
from app.web.utils import error_json_response


def login_check(func):
    @wraps(func)
    async def inner(self, *args, **kwargs):
        session = await get_session(self.request)
        if 'admin' not in session:
            return error_json_response(http_status=401)
        if session["admin"]['email'] != \
                (admin := await self.request.app.store.admins.get_by_email(
                    session["admin"]['email'])).email:
            return error_json_response(http_status=403)
        return await func(self, admin, *args, **kwargs)
    return inner
