import asyncio
import aiohttp
from app.store.yandex_dict_api.schemas import Word
from dataclasses import dataclass

from app.web.config import config_env


@dataclass
class YandexDictAccessor:
    token: str
    url = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key="

    async def check_word_(self, text: str, lang: str = "ru-ru") -> bool:
        self.url = self.url + f"{self.token}&lang={lang}&text={text}"

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as resp:
                if resp.status == 200 and (word := (await resp.json()).get("def", None)):
                    word = Word.Schema().load(word[0])

                    return word.pos == "noun"
                else:
                    return False


async def check_word(text: str, lang: str = "ru-ru") -> bool:
    url = (
        f"https://dictionary.yandex.net/api/v1/dicservice.json/lookup?key="
        f"{config_env['YANDEX_DICT_TOKEN']}&lang={lang}&text={text}"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200 and (word := (await resp.json()).get("def", None)):
                word = Word.Schema().load(word[0])
                return word.pos == "noun"
            else:
                return False


if __name__ == "__main__":
    asyncio.run(check_word(text="Ароматный"))
