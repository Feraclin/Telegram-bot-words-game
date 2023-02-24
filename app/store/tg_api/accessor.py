from typing import Optional
import aiohttp

from app.store.tg_api.schemes import GetUpdatesResponse, SendMessageResponse


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
                return GetUpdatesResponse.Schema().load(res_dict)
        except* ValueError as e:
            print(f"Failed to load schema {e}")

    async def send_message(self, chat_id: int, text: str, force_reply: bool = False) -> SendMessageResponse:
        url = self.get_url("sendMessage")
        payload = {
            'chat_id': chat_id,
            'text': text,
            'force_reply': force_reply
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)

    async def send_keyboard(self,
                            chat_id: int,
                            text: str = 'Pick on me',
                            keyboard: dict = None) -> None:
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
                                      mentinion: str,
                                      keyboard: dict):
        url = self.get_url("sendMessage")
        payload = {
            'chat_id': chat_id,
            'text': mentinion,
            'reply_markup': keyboard,
            'parse_mode': "Markdown",
        }
        print(payload)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                res_dict = await resp.json()
                return SendMessageResponse.Schema().load(res_dict)
