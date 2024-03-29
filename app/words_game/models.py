from sqlalchemy import ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, MappedAsDataclass

from app.store.database.sqlalchemy_base import DB, bigint


class User(MappedAsDataclass, DB):
    """
    Класс, представляющий пользователя.

    :param id: Идентификатор пользователя.
    :param username: Имя пользователя.
    :param total_point: Общее количество очков пользователя.
    """
    __tablename__ = "users"

    id: Mapped[bigint] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)
    total_point: Mapped[int] = mapped_column(nullable=True, default=0)


class GameSession(MappedAsDataclass, DB):
    """
    Класс, представляющий сессию игры.
    :param id: Идентификатор сессии.
    :param game_type: Тип игры.
    :param chat_id: Идентификатор чата.
    :param next_user_id: Идентификатор следующего игрока.
    :param next_user: Следующий игрок.
    :param creator_id: Идентификатор создателя игровой сессии.
    :param creator: Создатель игровой сессии.
    :param winner_id: Идентификатор победителя игры.
    :param winner: Победитель игры.
    :param is_active: Флаг активности игровой сессии.
    :param next_start_letter: Следующая буква.
    :param current_poll_id: Идентификатор текущего голосования.
    :param response_time: Время на ответ пользователя.
    :param anonymous_poll: Флаг анонимности голосования.
    :param poll_time: Время на голосование.
    :param life: Количество жизней.
    """
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_type: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[bigint] = mapped_column(nullable=False)
    words: Mapped[str] = mapped_column(nullable=True)
    next_user_id: Mapped[bigint] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    next_user: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[next_user_id])
    creator_id: Mapped[bigint] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    creator: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[creator_id])
    winner_id: Mapped[bigint] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    winner: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[winner_id])
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    next_start_letter: Mapped[str] = mapped_column(default=None, nullable=True)
    current_poll_id: Mapped[bigint] = mapped_column(default=None, nullable=True)
    response_time: Mapped[int] = mapped_column(nullable=False, default=15)
    anonymous_poll: Mapped[bool] = mapped_column(nullable=False, default=True)
    poll_time: Mapped[int] = mapped_column(nullable=False, default=15)
    life: Mapped[int] = mapped_column(nullable=False, default=3)


class UserGameSession(MappedAsDataclass, DB):
    __tablename__ = "user_game_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    game_sessions_id: Mapped[int] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE")
    )
    player_id: Mapped[bigint] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    game_session: Mapped[GameSession] = relationship(
        GameSession, backref="user_game_sessions", lazy="joined"
    )
    player: Mapped[User] = relationship(User, backref="user_game_sessions", lazy="joined")
    life: Mapped[int] = mapped_column(default=3)
    round_: Mapped[int] = mapped_column(nullable=True, default=0)
    point: Mapped[int] = mapped_column(nullable=True, default=0)
    poll_answer: Mapped[bool] = mapped_column(nullable=True, default=None)


class UsedCity(MappedAsDataclass, DB):
    __tablename__ = "used_cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id", ondelete="CASCADE"))
    city: Mapped["City"] = relationship("City", backref="used_cities", lazy="joined")
    game_session: Mapped[GameSession] = relationship(
        GameSession, backref="used_cities", lazy="joined"
    )


class City(MappedAsDataclass, DB):
    __tablename__ = "city"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)


class Words(MappedAsDataclass, DB):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(nullable=False, unique=True)


class WordsInGame(MappedAsDataclass, DB):
    __tablename__ = "words_in_game"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    game_session: Mapped[GameSession] = relationship(
        GameSession, backref="words_in_game", lazy="joined"
    )
    word: Mapped[Words] = relationship(Words, backref="words_in_game", lazy="joined")


class GameSettings(MappedAsDataclass, DB):
    __tablename__ = "game_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    response_time: Mapped[int] = mapped_column(nullable=False, default=15)
    anonymous_poll: Mapped[bool] = mapped_column(nullable=False, default=True)
    poll_time: Mapped[int] = mapped_column(nullable=False, default=15)
    life: Mapped[int] = mapped_column(nullable=False, default=3)

    _instance = None

    @classmethod
    async def get_instance(cls, session):
        if cls._instance is None:
            async with session() as session:
                cls._instance = (await session.execute(select(cls))).scalar_one_or_none()
                if cls._instance is None:
                    cls._instance = cls()
                    session.add(cls._instance)
                    await session.commit()
        return cls._instance
