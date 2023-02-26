from typing import ClassVar, Type

from marshmallow_dataclass import dataclass
from marshmallow import Schema, EXCLUDE


@dataclass
class Word:
    text: str
    pos: str

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE
