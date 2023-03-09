import asyncio
from abc import ABC
from unittest.mock import AsyncMock
from asyncio import current_task
import pytest
from aioresponses import aioresponses
from sqlalchemy import event, URL, text
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.sender.sender import Sender
from app.web.config import config as cfg
from app.words_game.models import GameSession
from app.worker_app.worker import Worker


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope="session")
async def sender():
    sender = Sender(cfg=cfg)


@pytest.fixture(scope="session")
async def worker():

    worker = Worker(cfg=cfg)
    worker.rabbitMQ = AsyncMock()
    try:
        await worker.database.connect()
        return worker
    finally:
        await worker.database.disconnect()


class TestSession(AsyncSession, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.begin_nested()

        @event.listens_for(self, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.expire_all()
                session.begin_nested()


sync_maker = sessionmaker()
Session = async_scoped_session(async_sessionmaker(autoflush=False, class_=TestSession, sync_session_class=sync_maker), scopefunc=current_task)


@pytest.fixture(scope="session")
def engine():

    engine_ = create_async_engine(
        url=URL.create(
                drivername="postgresql+asyncpg",
                host=cfg.database.host,
                database=cfg.database.database,
                username=cfg.database.user,
                password=cfg.database.password,
                port=cfg.database.port,
            ),
        echo=False
    )
    yield engine_


@pytest.fixture
async def session(engine):
    connection = await engine.connect()
    async with connection.begin() as transaction:

        Session.configure(bind=engine)
        session = Session()

        try:
            yield session
        finally:
            await Session.remove()
            await transaction.rollback()
            await connection.close()

@event.listens_for(sync_maker, "before_commit")
def before_commit(session):
    print("before commit")


@pytest.fixture(autouse=True)
async def mock_response():
    with aioresponses(passthrough=["http://127.0.0.1"]) as responses_mock:
        yield responses_mock


@pytest.fixture
async def game(session):
    game = GameSession(game_type="group",
                       chat_id=999999,
                       is_active=True,
                       id=999999,
                       winner=None,
                       winner_id=None,
                       creator_id=None,
                       creator=None,
                       next_user_id=None,
                       next_user=None,
                       words=[])
    session.add(game)
    await session.commit()
    return game
