import asyncio
from typing import Dict, Any
from unittest.mock import AsyncMock
import pytest
from aio_pika.abc import AbstractIncomingMessage, AbstractMessage
from aioresponses import aioresponses
from sqlalchemy import event, URL, create_engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session

from app.sender_app.sender import Sender
from app.web.config import config as cfg
from app.words_game.models import GameSession, User, City
from app.worker_app.worker import Worker
from app.store.database import DB

url = URL.create(
    drivername="postgresql+psycopg2",
    host=cfg.database.host,
    database=cfg.database.database,
    username=cfg.database.user,
    password=cfg.database.password,
    port=cfg.database.port,
)


@pytest.fixture(autouse=True)
async def mock_response():
    with aioresponses(passthrough=["http://127.0.0.1"]) as responses_mock:
        yield responses_mock


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture(scope="session")
async def sender():
    sender = Sender(cfg=cfg)
    return sender


@pytest.fixture(scope="session")
async def worker():

    worker = Worker(cfg=cfg)
    worker.rabbitMQ = AsyncMock()
    try:
        await worker.database.connect()
        return worker
    finally:
        await worker.database.disconnect()


@pytest.fixture(autouse=True)
async def mock_response():
    with aioresponses(passthrough=["http://127.0.0.1"]) as responses_mock:
        yield responses_mock


class TestSession(Session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.begin_nested()

        @event.listens_for(self, "after_transaction_end")
        def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                session.expire_all()
                session.begin_nested()


Session = scoped_session(sessionmaker(autoflush=False, class_=TestSession))


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(
        url=url,
        future=True,
    )
    DB.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()

    Session.configure(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        Session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
async def city(session):
    city = City(id=200000,
                name="test_city")
    session.add(city)
    session.commit()
    try:
        yield city
    finally:
        session.delete(city)
        session.commit()


@pytest.fixture(scope="function")
async def user(session):
    user = User(
        username="test_user",
        id=50000,
    )

    session.add(user)
    session.commit()
    try:
        yield user
    finally:
        session.delete(user)
        session.commit()


@pytest.fixture(scope="function")
async def user1(session):
    user = User(
        username="test_user1",
        id=50001,
    )

    session.add(user)
    session.commit()
    try:
        yield user
    finally:
        session.delete(user)
        session.commit()


@pytest.fixture(scope="function")
async def user2(session):
    user = User(
        username="test_user2",
        id=50002,
    )

    session.add(user)
    session.commit()
    try:
        yield user
    finally:
        session.delete(user)
        session.commit()


@pytest.fixture(scope="function")
async def game(session, user, user1):
    game = GameSession(
        game_type="group",
        chat_id=200,
        is_active=True,
        id=50000,
        winner=None,
        winner_id=None,
        creator_id=user.id,
        creator=user,
        next_user_id=user1.id,
        next_user=user1,
        words=[]
    )
    session.add(game)
    session.commit()
    try:
        yield game
    finally:
        session.delete(game)
        session.commit()


async def test_game_session_exists(session, game):
    game_session = session.get(GameSession, game.id)
    assert game_session is not None
    assert game_session.id == game.id


class IncomingMessage(AbstractIncomingMessage):
    def __copy__(self) -> "AbstractMessage":
        pass

    def info(self) -> Dict[str, Any]:
        pass

    def __init__(self, body, routing_key):
        self.body = body
        self.routing_key = routing_key

    def __iter__(self):
        yield self.body

    async def ack(self, **kwargs):
        pass

    def channel(self):
        pass

    def headers(self):
        pass

    def lock(self):
        pass

    def locked(self):
        pass

    def nack(self, **kwargs):
        pass

    def process(self, **kwargs):
        pass

    def processed(self):
        pass

    def properties(self):
        pass

    def reject(self, **kwargs):
        pass
