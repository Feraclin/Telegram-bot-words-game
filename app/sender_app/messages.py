# messages
from dataclasses import dataclass, field
from typing import List, Dict

# reply_keyboards
keyboard_private_play = {
    "keyboard": [[{"text": "/yes"}, {"text": "/no"}]],
    "resize_keyboard": True,
    "one_time_keyboard": True,
    "selective": True,
    "input_field_placeholder": "You wanna play?",
}


# inline_keyboards
keyboard_team = {
    "inline_keyboard": [
        [{"text": "Yes", "callback_data": "/yes"}, {"text": "No", "callback_data": "/no"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": True,
}

keyboards = {"start_keyboard": keyboard_private_play, "keyboard_team": keyboard_team}


class PrivatePlayKeyboard:
    keyboard: List[List[Dict[str, str]]] = field(default_factory=list)
    resize_keyboard: bool = True
    one_time_keyboard: bool = True
    selective: bool = True
    input_field_placeholder: str = "You wanna play?"

    def __post_init__(self):
        if not self.keyboard:
            self.keyboard = [[{"text": "/yes"}, {"text": "/no"}]]

    def __str__(self):
        return {
            "keyboard": self.keyboard,
            "resize_keyboard": self.resize_keyboard,
            "one_time_keyboard": self.one_time_keyboard,
            "selective": self.selective,
            "input_field_placeholder": self.input_field_placeholder,
        }


@dataclass
class TeamKeyboard:
    inline_keyboard: List[List[Dict[str, str]]] = field(default_factory=list)
    resize_keyboard: bool = True
    one_time_keyboard: bool = True

    def __post_init__(self):
        if not self.inline_keyboard:
            self.inline_keyboard = [
                [{"text": "Yes", "callback_data": "/yes"}, {"text": "No", "callback_data": "/no"}]
            ]

    def __str__(self):
        return {
            "inline_keyboard": self.inline_keyboard,
            "resize_keyboard": self.resize_keyboard,
            "one_time_keyboard": self.one_time_keyboard,
        }
