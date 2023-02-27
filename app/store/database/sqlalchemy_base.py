from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Annotated


bigint = Annotated[int, "bigint"]


class DB(DeclarativeBase):
    type_annotation_map = {
        bigint: BigInteger,
    }

