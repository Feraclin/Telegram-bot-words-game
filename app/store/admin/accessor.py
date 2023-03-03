from hashlib import sha256

from sqlalchemy import select, insert

from app.admin.models import Admin, AdminModel
from app.base.base_accessor import BaseAccessor


class AdminAccessor(BaseAccessor):
    async def get_by_email(self, email: str) -> Admin | None:
        res = await self.app.database.execute_query(select(AdminModel).where(AdminModel.email == email))

        admin = res.scalar()
        if admin:
            return admin.to_dc()
        else:
            return None

    async def create_admin(self, email: str, password: str) -> Admin:
        res = await self.get_by_email(email=email)

        if res:
            return res

        res = await self.app.database.scalars_query(
            insert(AdminModel).returning(AdminModel),
            [{"email": email, "password": sha256(password.encode()).hexdigest()}],
        )
        self.logger.info("Admin created")

        return res.one().to_dc()
