from sender import Sender
from app.web.config import config
from starter import starter

if __name__ == "__main__":

    sender = Sender(config)
    starter(start_tasks=[sender.start],
            stop_tasks=[sender.stop])
