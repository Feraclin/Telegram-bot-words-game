import asyncio
import logging
from .messages import keyboards

import bson

from app.store.tg_api.client import TgClient

from app.web.config import ConfigEnv, config
from app.store.rabbitMQ.rabbitMQ import RabbitMQ


class Sender:

    def __init__(self, cfg: ConfigEnv, concurrent_workers: int = 1):
        self.cfg = cfg
        self.concurrent_workers = concurrent_workers
        self._tasks = []
        self.logger = logging.getLogger("sender")
        self.tg_client = TgClient(token=self.cfg.tg_token.tg_token)
        self.rabbitMQ = RabbitMQ(
            host=self.cfg.rabbitmq.host,
            port=self.cfg.rabbitmq.port,
            user=self.cfg.rabbitmq.user,
            password=self.cfg.rabbitmq.password,
        )
        self.routing_key_worker = "worker"
        self.routing_key_sender = "sender"
        self.queue_name = "tg_bot_sender"

    async def on_message(self, message):
        upd = bson.loads(message.body)
        await self.handle_update(upd)
        await message.ack()

    async def start(self):
        await self.rabbitMQ.connect()
        self._tasks = [
            asyncio.create_task(self._worker_rabbit()) for _ in range(self.concurrent_workers)
        ]

    async def stop(self):
        for task_ in self._tasks:
            task_.cancel()
        await self.rabbitMQ.disconnect()

    async def _worker_rabbit(self):
        await self.rabbitMQ.listen_events(
            on_message_func=self.on_message,
            queue_name=self.queue_name,
            routing_key=[self.routing_key_sender],
        )

    async def handle_update(self, upd: dict):
        match upd.get("type_"):
            case "message":
                await self.tg_client.send_message(
                    chat_id=upd["chat_id"],
                    text=upd["text"],
                    force_reply=upd.get("force_reply", False),
                )
            case "message_keyboard":
                keyboard = await self.tg_client.send_keyboard(
                    chat_id=upd["chat_id"],
                    text=upd["text"],
                    keyboard=keyboards[upd["keyboard"]])
                if upd.get("live_time", None):
                    upd["keyboard_message_id"] = keyboard.result.message_id
                    upd["type_"] = "message_inline_remove_keyboard"
                    await self.rabbitMQ.send_event(
                        message=upd,
                        routing_key=self.routing_key_sender,
                        delay=upd["live_time"] * 1000,
                    )
            case "message_inline_remove_keyboard":
                await self.tg_client.remove_inline_keyboard(
                    chat_id=upd["chat_id"],
                    message_id=upd["keyboard_message_id"]
                )
                message = {"type_": "pick_leader",
                           "chat_id": upd["chat_id"]}
                await self.rabbitMQ.send_event(message=message,
                                               routing_key=self.routing_key_worker)
            case "callback_alert":
                await self.tg_client.send_callback_alert(
                    callback_id=upd["callback_id"],
                    text=upd["text"],
                )
            case "send_poll":
                poll = await self.tg_client.send_poll(
                    chat_id=upd["chat_id"],
                    question=upd["question"],
                    options=upd["options"],
                    anonymous=upd["anonymous"],
                    period=10,
                )
                upd["type_"] = "send_poll_answer"
                upd["poll_message_id"] = poll.result.message_id
                upd["poll_id"] = poll.result.poll.id
                await self.rabbitMQ.send_event(message=upd,
                                               routing_key=self.routing_key_sender,
                                               delay=12000)
            case "send_poll_answer":
                await self.check_poll(upd)
            case _:
                self.logger.error(f"Unknown type: {upd['type_']}")

    async def check_poll(self, upd: dict):
        poll = await self.tg_client.remove_inline_keyboard(
            chat_id=upd["chat_id"],
            message_id=upd["poll_message_id"],
        )
        word = poll.result.poll.question.split()[4]
        answers = poll.result.poll.options
        yes = 0
        no = 0
        for ans in answers:
            match ans.text:
                case "Yes":
                    yes = ans.voter_count
                case "No":
                    no = ans.voter_count

        if yes > no:
            res_poll = "yes"
        else:
            res_poll = "no"

            await self.tg_client.send_message(
                chat_id=upd["chat_id"],
                text=f"{word} - нет такого слова"
            )
        message_poll_result = {
            "type_": "poll_result",
            "chat_id": upd["chat_id"],
            "poll_id": upd["poll_id"],
            "poll_result": res_poll,
            "word": word,
        }

        await self.rabbitMQ.send_event(message=message_poll_result,
                                       routing_key=self.routing_key_worker)


if __name__ == "__main__":
    sender = Sender(cfg=config)

    loop = asyncio.new_event_loop()

    try:
        loop.create_task(sender.start())
        loop.run_forever()

    except KeyboardInterrupt:
        pass
    finally:
        loop.create_task(sender.stop())
        for t in (tasks_ := asyncio.all_tasks(loop)):
            t.cancel()
        loop.run_until_complete(asyncio.gather(*tasks_, return_exceptions=True))
