from dataclasses import dataclass
from hashlib import sha256
from typing import Optional, TYPE_CHECKING, Union

from sqlalchemy.orm import Mapped, mapped_column

from app.store.database.sqlalchemy_base import DB
if TYPE_CHECKING:
    from aiohttp_session import Session


@dataclass
class Admin:
    id: int
    email: str
    password: str | None = None

    def is_password_valid(self, password: str):
        return self.password == sha256(password.encode()).hexdigest()

    @classmethod
    def from_session(cls, session: Union["Session", dict]) -> Optional["Admin"]:
        return cls(id=session["admin"]["id"], email=session["admin"]["email"])

    def check_password(self, password) -> bool:
        return self.password != sha256(password.encode("utf-8")).hexdigest()


class AdminModel(DB):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)

    def to_dc(self) -> Admin:
        return Admin(id=self.id,
                     email=self.email,
                     password=self.password)
