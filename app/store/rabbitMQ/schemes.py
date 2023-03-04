
from typing import ClassVar, Type

from marshmallow_dataclass import dataclass
from marshmallow import Schema, EXCLUDE


@dataclass
class MessageRabbitMQ:
    type_: str
    chat_id: int | None = None
    user_id: int | None = None
    text: str | None = None

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE
