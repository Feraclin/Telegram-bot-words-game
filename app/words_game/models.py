from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, MappedAsDataclass

from app.store.database.sqlalchemy_base import DB, bigint, list_str


class User(MappedAsDataclass, DB):
    __tablename__ = "users"

    id: Mapped[bigint] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)
    total_point: Mapped[int] = mapped_column(nullable=True, default=0)


class GameSession(MappedAsDataclass, DB):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_type: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[bigint] = mapped_column(nullable=False)
    words: Mapped[list_str] = mapped_column(nullable=True)
    next_user_id: Mapped[bigint] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    next_user: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[next_user_id])
    user_id: Mapped[bigint] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    user: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[user_id])
    winner_id: Mapped[bigint] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    winner: Mapped[User] = relationship(User, lazy="joined", foreign_keys=[winner_id])
    status: Mapped[bool] = mapped_column(nullable=False, default=False)
    next_start_letter: Mapped[str] = mapped_column(default=None, nullable=True)
    current_poll_id: Mapped[bigint] = mapped_column(default=None, nullable=True)


class Team(MappedAsDataclass, DB):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)

    game_sessions_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    player_id: Mapped[bigint] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    game_session: Mapped[GameSession] = relationship(GameSession, backref="teams")
    players: Mapped[list[User]] = relationship(User, backref="teams")
    life: Mapped[int] = mapped_column(default=3)
    round_: Mapped[int] = mapped_column(nullable=True, default=0)
    point: Mapped[int] = mapped_column(nullable=True, default=0)


class UsedCity(MappedAsDataclass, DB):
    __tablename__ = "used_cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"))
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id", ondelete="CASCADE"))
    city: Mapped["City"] = relationship("City", backref="used_cities", lazy="joined")
    game_session: Mapped[GameSession] = relationship(GameSession, backref="used_cities", lazy="joined")


class City(MappedAsDataclass, DB):
    __tablename__ = "city"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
