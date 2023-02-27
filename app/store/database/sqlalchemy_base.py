from sqlalchemy import BigInteger, String
from sqlalchemy.orm import DeclarativeBase
from typing_extensions import Annotated
from sqlalchemy.types import ARRAY

bigint = Annotated[int, "bigint"]
list_str = Annotated[list[str], "list"]


class DB(DeclarativeBase):
    type_annotation_map = {
        bigint: BigInteger,
        list_str: ARRAY(String)
    }
