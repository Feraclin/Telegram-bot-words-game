from poller import Poller
from app.web.config import config
from starter import starter

if __name__ == "__main__":
    poller = Poller(cfg=config)
    starter(start_tasks=[poller.start],
            stop_tasks=[poller.stop])
