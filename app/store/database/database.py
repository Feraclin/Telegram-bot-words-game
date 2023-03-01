from typing import TYPE_CHECKING, Optional

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_scoped_session, create_async_engine, \
    async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.store.database import DB

if TYPE_CHECKING:
    from app.web.app import Application


class Database:
    def __init__(self, app: Optional["Application"] = None, url: Optional[str] = None):
        self.app = app
        self.URL_DB = URL.create(drivername="postgresql+asyncpg",
                                 host=app.config.database.host,
                                 database=app.config.database.database,
                                 username=app.config.database.user,
                                 password=app.config.database.password,
                                 port=app.config.database.port) if app else url
        self.engine_: AsyncEngine | None = None
        self.db_: DeclarativeBase | None = None
        self.session: AsyncSession | async_scoped_session | sessionmaker | async_sessionmaker | None = None

    async def connect(self, *_: list, **__: dict) -> None:
        self.db_ = DB
        self.engine_ = create_async_engine(self.URL_DB,
                                           future=True,
                                           echo=False
                                           )
        self.session = async_sessionmaker(
            bind=self.engine_,
            expire_on_commit=False,
            autoflush=True,
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
