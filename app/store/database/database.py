import logging
from typing import TYPE_CHECKING, Optional

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.store.database import DB


if TYPE_CHECKING:
    from app.web.app import Application
    from app.web.config import ConfigEnv


class Database:
    def __init__(
        self,
        app: Optional["Application"] = None,
        cfg: Optional["ConfigEnv"] = None,
    ):
        if app:
            self.app = app
            self.URL_DB = URL.create(
                drivername="postgresql+asyncpg",
                host=app.config.database.host,
                database=app.config.database.database,
                username=app.config.database.user,
                password=app.config.database.password,
                port=app.config.database.port,
            )
        elif cfg:
            self.URL_DB = URL.create(
                drivername="postgresql+asyncpg",
                host=cfg.database.host,
                database=cfg.database.database,
                username=cfg.database.user,
                password=cfg.database.password,
                port=cfg.database.port,
            )
        self.engine_: AsyncEngine | None = None
        self.db_: DeclarativeBase | None = None
        self.session: AsyncSession | async_scoped_session | sessionmaker | async_sessionmaker | None = None
        self.logger = logging.getLogger("database")

    async def connect(self, *_: list, **__: dict) -> None:
        self.db_ = DB
        self.engine_ = create_async_engine(self.URL_DB, future=True, echo=False)
        self.session = async_sessionmaker(
            bind=self.engine_,
            expire_on_commit=False,
            autoflush=True,
        )

    async def execute_query(self, query):
        async with self.session() as session:
            res = await session.execute(query)
            await session.commit()
        await self.engine_.dispose()
        return res

    async def scalars_query(self, query, values_list: list | None):
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
        try:
            await self.engine_.dispose()
        except Exception as e:
            self.logger.info(f"Disconnect from engine error {e}")
