import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.store import Database
from app.store.database import DB
from app.store.words_game.accessor import WGAccessor
from app.words_game.models import GameSession, User, City
from app.web.config import ConfigEnv, config as cfg

@pytest.fixture(scope="module")
def db():
    db = Database(cfg=cfg)
    db.engine_ = create_engine(url=("sqlite:///:memory:"))
    db.connect()

    DB.metadata.create_all(db.engine_)
    print(db)
    Session = db.session()
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
async def accessor(db):
    accessor = WGAccessor(database=db)
    yield accessor


@pytest.mark.asyncio
async def test_create_game_session(accessor):
    game_session = await accessor.create_game_session(user_id=1, chat_id=1, chat_type="private")
    assert isinstance(game_session, GameSession)
