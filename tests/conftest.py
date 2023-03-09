import asyncio
from random import randint
from unittest.mock import AsyncMock
import pytest
from aioresponses import aioresponses
from sqlalchemy import event, URL, text, create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers, Session, scoped_session

from app.sender.sender import Sender
from app.web.config import config as cfg
from app.words_game.models import GameSession, User
from app.worker_app.worker import Worker


url = URL.create(
    drivername="postgresql+asyncpg",
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
        url=URL.create(
            drivername="postgresql",
            host=cfg.database.host,
            database=cfg.database.database,
            username=cfg.database.user,
            password=cfg.database.password,
            port=cfg.database.port,
        ),
        # echo=True,
        future=True,
    )
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
async def user(session):
    user = User(
        username="test_user",
        id=randint(1, 100000000),
    )

    session.add(user)
    session.commit()
    try:
        yield user
    finally:
        session.delete(user)
        session.commit()


@pytest.fixture(scope="function")
async def game(session, user):
    game = GameSession(
        game_type="group",
        chat_id=randint(1, 100000000),
        is_active=True,
        id=randint(1, 100000000),
        winner=None,
        winner_id=None,
        creator_id=user.id,
        creator=user,
        next_user_id=None,
        next_user=None,
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


async def test_pick_city(worker: Worker, session, game):
    await worker.pick_city(
        user_id=game.creator_id,
        chat_id=game.chat_id,
        username="test_user",
        letter="А"
    )
    game_session = session.get(GameSession, game.id)
    print(game)
    assert game_session.next_start_letter is None

