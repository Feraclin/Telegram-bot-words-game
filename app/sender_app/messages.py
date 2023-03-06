# messages

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

keyboards = {"start_keyboard": keyboard_private_play,
             "keyboard_team": keyboard_team}
