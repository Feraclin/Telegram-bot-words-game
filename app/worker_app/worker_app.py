import asyncio

from app.web.config import config
from app.worker_app.worker import Worker


if __name__ == "__main__":
    worker = Worker(cfg=config)

    loop = asyncio.new_event_loop()

    try:
        loop.create_task(worker.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(worker.stop())
