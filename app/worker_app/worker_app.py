import asyncio

from app.web.config import config
from worker import Worker


if __name__ == "__main__":
    worker = Worker(cfg=config)

    loop = asyncio.new_event_loop()

    try:
        loop.create_task(worker.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.create_task(worker.stop())
        for t in (tasks_ := asyncio.all_tasks(loop)):
            t.cancel()
        loop.run_until_complete(asyncio.gather(*tasks_, return_exceptions=True))
