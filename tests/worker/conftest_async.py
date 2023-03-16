import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import event, URL
from random import randint
from app.web.config import config as cfg
from app.words_game.models import User, GameSession

url = URL.create(
    drivername="postgresql+asyncpg",
    host=cfg.database.host,
    database=cfg.database.database,
    username=cfg.database.user,
    password=cfg.database.password,
    port=cfg.database.port,
)


class TestSession(AsyncSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.begin_nested()

        @event.listens_for(self, "after_transaction_end")
        async def restart_savepoint(session, transaction):
            if transaction.nested and not transaction._parent.nested:
                await session.expire_all()
                await session.begin_nested()


async_engine = create_async_engine(url=url, future=True)

Session = scoped_session(sessionmaker(class_=TestSession,
                                      autoflush=False,
                                      bind=async_engine))

@pytest.fixture(scope="session")
async def engine():
    async_engine_ = create_async_engine(url=url, future=True)
    try:
        yield async_engine_
    finally:
        await async_engine_.dispose()


@pytest.fixture
async def session(engine):
    async with engine.begin() as conn:
        Session.configure(bind=conn)
        async with Session() as session:

            try:
                yield session
            finally:
                await session.close()


@pytest.fixture(scope="function")
async def user(session):
    user = User(username="test_user", id=randint(1, 100000000), )

    session.add(user)
    await session.commit()
    try:
        yield user
    finally:
        session.delete(user)
        await session.commit()


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