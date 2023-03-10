from dataclasses import dataclass

help_msg = """
f'Список команд:
/play - запустить игру,
/stop - остановить игру,
/ping проверка работы,
/help - справка.
При ответе город или слово следует вводить как команду начиная с /')
"""


@dataclass
class GameSettings:
    response_time: int
    anonymous_poll: bool
    poll_time: int
