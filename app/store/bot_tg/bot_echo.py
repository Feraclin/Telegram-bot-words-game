import asyncio

from dotenv import find_dotenv, dotenv_values

from app.store.tg_api.accessor import TgClient

found_dotenv = find_dotenv(filename='.env')
config_env = dotenv_values(found_dotenv)
token_tg = config_env['BOT_TOKEN_TG']


async def run_echo(flag: bool = True, token: str = token_tg):
    c = TgClient(token=token)

    offset = 0
    while flag:
        res = await c.get_updates_in_objects(offset=offset, timeout=60)
        for item in res.result:
            print(item)
            offset = item.update_id + 1
            if item.message:
                if item.message.text == 'stop':
                    loop.stop()
                await c.send_message(item.message.chat.id, item.message.text)
            elif item.callback_query:
                await c.send_message(item.callback_query.from_.id, item.callback_query.from_.first_name)


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.create_task(run_echo(token=token_tg))
    loop.run_forever()
