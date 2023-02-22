from asyncio import current_task
from typing import Optional, TYPE_CHECKING

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_scoped_session, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.store.database import DB

if TYPE_CHECKING:
    from app.web.app import Application


class Database:
    def __init__(self, app: "Application"):
        self.app = app
        self.URL_DB = URL.create(drivername="postgresql+asyncpg",
                                 host=app.config.database.host,
                                 database=app.config.database.database,
                                 username=app.config.database.user,
                                 password=app.config.database.password,
                                 port=app.config.database.port)
        self.engine_: Optional[AsyncEngine] = None
        self.db_: Optional[DeclarativeBase] = None
        self.session: Optional[AsyncSession, async_scoped_session, sessionmaker] = None

    async def connect(self, *_: list, **__: dict) -> None:
        self.db_ = DB
        self.engine_ = create_async_engine(self.URL_DB,
                                           future=True,
                                           echo=False
                                           )
        self.session =sessionmaker(
            bind=self.engine_,
            expire_on_commit=False,
            autoflush=True,
            class_=AsyncSession
        )
        await self.app.store.admins.create_admin(email=self.app.config.admin.email,
                                                 password=self.app.config.admin.password)

    async def execute_query(self,
                            query):
        async with self.session() as session:
            res = await session.execute(query)
            await session.commit()
        await self.engine_.dispose()
        return res

    async def scalars_query(self,
                            query,
                            values_list: list | None):
        async with self.session() as session:
            res = await session.scalars(query, values_list)
            await session.commit()
        await self.engine_.dispose()
        return res

    async def add_query(self, model) -> None:
        async with self.session.begin() as session:
            session.add(model)
        await self.engine_.dispose()

    async def disconnect(self, *_: list, **__: dict) -> None:
        pass
