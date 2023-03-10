import asyncio

from sender import Sender
from app.web.config import config


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
