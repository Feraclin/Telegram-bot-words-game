# Структура бота из статьи https://habr.com/ru/company/kts/blog/598575/

from dataclasses import field
from typing import ClassVar, Type

from marshmallow_dataclass import dataclass
from marshmallow import Schema, EXCLUDE


@dataclass
class MessageFrom:
    id: int
    first_name: str
    last_name: str | None
    username: str

    class Meta:
        unknown = EXCLUDE


@dataclass
class Chat:
    id: int
    type: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    title: str | None = None

    class Meta:
        unknown = EXCLUDE


@dataclass
class PollAnswer:
    poll_id: int | None = None
    user: MessageFrom | None = None
    option_ids: list[int] | None = None

    class Meta:
        unknown = EXCLUDE


@dataclass
class PollOption:
    text: str | None = None
    voter_count: int | None = None

    class Meta:
        unknown = EXCLUDE


@dataclass
class Poll:
    id: int
    question: str
    options: list[PollOption]
    total_voter_count: int
    is_closed: bool
    is_anonymous: bool
    type: str
    allow_multiple_answers: bool | None
    correct_option_id: int | None

    class Meta:
        unknown = EXCLUDE


@dataclass
class Message:
    message_id: int
    from_: MessageFrom = field(metadata={"data_key": "from"})
    chat: Chat
    date: int
    text: str | None = 'Картинки не смотрю'
    poll: Poll | None = None

    class Meta:
        unknown = EXCLUDE


@dataclass
class CallbackQuery:
    id: str
    from_: MessageFrom = field(metadata={"data_key": "from"})
    message: Message
    data: str

    class Meta:
        unknown = EXCLUDE


@dataclass
class ChatMember:
    date: int

    class Meta:
        unknown = EXCLUDE


@dataclass
class UpdateObj:
    update_id: int | None = None
    message: Message | None = None
    callback_query: CallbackQuery | None = None
    my_chat_member: ChatMember | None = None
    poll: Poll | None = None
    poll_answer: PollAnswer | None = None

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE


@dataclass
class GetUpdatesResponse:
    ok: bool
    result: list[UpdateObj]

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE


@dataclass
class SendMessageResponse:
    ok: bool
    result: Message

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE


@dataclass
class PollResultSchema:
    ok: bool
    result: Message

    Schema: ClassVar[Type[Schema]] = Schema

    class Meta:
        unknown = EXCLUDE
