from pprint import pprint

import pytest
from app.store.tg_api.schemes import GetUpdatesResponse, UpdateObj, Message, Chat, MessageFrom, Poll, PollOption, PollAnswer, CallbackQuery, ChatMember


@pytest.fixture
def message_from():
    return MessageFrom(id=1, first_name="John", last_name="Doe", username="johndoe")


@pytest.fixture
def chat():
    return Chat(id=1, type="private", first_name="John", last_name="Doe", username="johndoe")


@pytest.fixture
def poll_option():
    return PollOption(text="Option 1", voter_count=0)


@pytest.fixture
def poll(poll_option):
    return Poll(
        id=1,
        question="Question",
        options=[poll_option],
        total_voter_count=0,
        is_closed=False,
        is_anonymous=True,
        type="quiz",
        allow_multiple_answers=None,
        correct_option_id=None,
    )


@pytest.fixture
def message(message_from, chat, poll):
    return Message(
        message_id=1,
        from_=message_from,
        chat=chat,
        date=0,
        text="Hello",
        poll=poll,
    )


@pytest.fixture
def callback_query(message_from, message):
    return CallbackQuery(
        id="1",
        from_=message_from,
        message=message,
        data="data",
    )


@pytest.fixture
def chat_member():
    return ChatMember(date=0)


@pytest.fixture
def update_obj(message, callback_query, chat_member, poll, poll_answer):
    return UpdateObj(
        update_id=500,
        message=message,
        callback_query=callback_query,
        my_chat_member=chat_member,
        poll=poll,
        poll_answer=poll_answer,
    )


@pytest.fixture
def poll_answer():
    return PollAnswer(
        poll_id=1,
        user=None,
        option_ids=[1],
    )


@pytest.fixture
def get_updates_response(update_obj):
    return GetUpdatesResponse(ok=True, result=[update_obj])

@pytest.fixture
def get_updates_response_dict(update_obj):
    return GetUpdatesResponse.Schema().dump(GetUpdatesResponse(ok=True, result=[update_obj]))

def test_get_updates_response(get_updates_response):

    assert get_updates_response.ok
    assert len(get_updates_response.result) == 1
