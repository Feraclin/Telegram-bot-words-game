from dataclasses import dataclass

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, MappedAsDataclass

from app.store.database.sqlalchemy_base import DB


class User(MappedAsDataclass, DB):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(nullable=False)


class GameSession(MappedAsDataclass, DB):
    __tablename__ = 'game_sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[bool] = mapped_column(nullable=False, default=False)
    next_start_letter: Mapped[str] = mapped_column(default=None)
    next_player_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    next_player: Mapped[User] = relationship(User, backref='game_sessions', lazy='joined')
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    user: Mapped[User] = relationship(User, backref='game_sessions', lazy='joined')
    winner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    winner: Mapped[User] = relationship(User, backref='game_sessions', lazy='joined')


class Team(MappedAsDataclass, DB):
    __tablename__ = 'teams'

    id: Mapped[int] = mapped_column(primary_key=True)
    life: Mapped[int] = mapped_column(default=3)
    game_sessions_id: Mapped[int] = mapped_column(ForeignKey('game_sessions.id', ondelete='CASCADE'))
    player_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    game_session: Mapped[GameSession] = relationship(GameSession, backref='teams')
    players: Mapped[list[User]] = relationship(User, backref='teams')


class UsedCity(MappedAsDataclass, DB):
    __tablename__ = 'used_cities'

    id: Mapped[int] = mapped_column(primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey('game_sessions.id', ondelete='CASCADE'))
    city_id: Mapped[int] = mapped_column(ForeignKey('cities.id', ondelete='CASCADE'))
    city: Mapped["City"] = relationship('City', backref='used_cities', lazy='joined')
    game_session: Mapped[GameSession] = relationship(GameSession, backref='used_cities', lazy='joined')


class Country(MappedAsDataclass, DB):
    __tablename__ = 'country'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    regions: Mapped[list["Region"]] = relationship("Region", back_populates='country_name')


class Region(MappedAsDataclass, DB):
    __tablename__ = 'region'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey('country.id', ondelete='CASCADE'))
    cities: Mapped[list["City"]] = relationship("City", back_populates='region_name')
    country_name: Mapped[Country] = relationship(Country, back_populates='regions', lazy='joined')


class City(MappedAsDataclass, DB):
    __tablename__ = 'city'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    region_id: Mapped[int] = mapped_column(ForeignKey('region.id', ondelete='CASCADE'))
    region_name: Mapped[Region] = relationship(Region, back_populates='cities', lazy='joined')
