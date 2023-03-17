from app.web.config import config
from starter import starter
from worker import Worker

if __name__ == "__main__":
    worker = Worker(cfg=config)
    starter(start_tasks=[worker.start], stop_tasks=[worker.stop])
