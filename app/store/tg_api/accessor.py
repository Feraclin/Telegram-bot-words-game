from typing import Optional
import aiohttp

from app.store.tg_api.schemes import GetUpdatesResponse, SendMessageResponse, PollResultSchema


class TgClient:
    def __init__(self, token: str = ''):
        self.token = token

    def get_url(self, method: str):
        return f"https://api.telegram.org/bot{self.token}/{method}"

    async def get_me(self) -> dict:
        url = self.get_url("getMe")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.json()

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 0) -> dict:
        url = self.get_url("getUpdates")
        params = {}
        if offset:
            params['offset'] = offset
        if timeout:
            params['timeout'] = timeout
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                return await resp.json()

    async def get_updates_in_objects(self, offset: Optional[int] = None, timeout: int = 0) -> GetUpdatesResponse:
        res_dict = await self.get_updates(offset=offset, timeout=timeout)
        try:
            if res_dict.get('result') is not None:
                print(res_dict)
                return GetUpdatesResponse.Schema().load(res_dict)
        except* ValueError as e:
            print(f"Failed to load schema {e}")

    async def send_message(self, chat_id: int, text: str, force_reply: bool = False) -> SendMessageResponse:
        url = self.get_url("sendMessage")
        payload = {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': {"force_reply": force_reply,
                             "selective": True}
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)

    async def send_keyboard(self,
                            chat_id: int,
                            text: str = 'Pick on me',
                            keyboard: dict = None) -> SendMessageResponse:
        url = self.get_url("sendMessage")
        payload = {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': keyboard
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()

                return SendMessageResponse.Schema().load(res_dict)

    async def send_keyboard_to_player(self,
                                      chat_id: int,
                                      text: str,
                                      keyboard: dict):
        url = self.get_url("sendMessage")
        payload = {
            'chat_id': chat_id,
            'text': text,
            'reply_markup': keyboard,
            'parse_mode': "Markdown",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)

    async def send_poll(self,
                        chat_id: int,
                        question: str,
                        answers: list[str],
                        anonymous: bool = False,
                        period: int = 15
                        ) -> SendMessageResponse:
        url = self.get_url("sendPoll")
        payload = {
            'chat_id': chat_id,
            'question': question,
            'options': answers,
            'is_anonymous': anonymous,
            "open_period": period,
            'reply_markup': {'inline_keyboard': [[{"text": "About word", 'callback_data': '/pass'}]]}}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)

    async def remove_inline_keyboard(self,
                                     message_id: int,
                                     chat_id: int):
        url = self.get_url("editMessageReplyMarkup")
        payload = {
            "chat_id": chat_id,
            'message_id': message_id,
            'reply_markup': {'inline_keyboard': [[]]}}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                print(res_dict)
                return SendMessageResponse.Schema().load(res_dict)

    async def stop_poll(self,
                        chat_id: int,
                        message_id: int) -> PollResultSchema:
        url = self.get_url("stopPoll")
        payload = {
            'chat_id': chat_id,
            "message_id": message_id
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                print(res_dict)
                return PollResultSchema.Schema().load(res_dict)

    async def send_callback_alert(self, callback_id: str, text: str) -> int:
        url = self.get_url("answerCallbackQuery")
        payload = {
            "callback_query_id": callback_id,
            "text": text
                   }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return resp.status

    async def edit_message_text(self,
                                chat_id: int,
                                message_id: int):
        url = self.get_url("editMessageText")
        payload = {
            'chat_id': chat_id,
            "message_id": message_id,
            "text": "Мы учтем ваше мнение(нет)"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                print(res_dict)
                return SendMessageResponse.Schema().load(res_dict)