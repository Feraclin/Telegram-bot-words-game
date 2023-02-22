from aiohttp.web import HTTPForbidden
from aiohttp_apispec import request_schema, response_schema, docs
from aiohttp_session import new_session

from app.admin.schemes import AdminSchema
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class AdminLoginView(View):
    @docs(tags=["admin"], summary="Login Admin", description="Logged as admin")
    @request_schema(AdminSchema)
    @response_schema(AdminSchema, 200)
    async def post(self):
        print(self.data)
        email, password = self.data["email"], self.data["password"]
        # проверка наличия администратора с данным email и валидность пароля
        self.request.app.logger.info(f'{email}, {password}')
        admin = await self.request.app.store.admins.get_by_email(email)

        if not admin or admin.password != password:
            raise HTTPForbidden
        self.request.app.logger.info(admin)

        session = await new_session(request=self.request)
        session["admin"] = AdminSchema().dump(admin)
        self.request.app.logger.info("admin login successful")

        return json_response(data=AdminSchema().dump(admin))


class AdminCurrentView(AuthRequiredMixin, View):
    @docs(tags=["admin"], summary="Current Admin", description="id and email of current admin")
    @response_schema(AdminSchema, 200)
    async def get(self):
        self.request.app.logger.info("check current admin successful")
        return json_response(data=AdminSchema().dump(self.request.admin))
