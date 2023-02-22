from aiohttp.web_exceptions import HTTPBadRequest
from marshmallow import Schema, fields, pre_load


class ThemeSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)


class QuestionSchema(Schema):
    id = fields.Int(required=False)
    title = fields.Str(required=True)
    theme_id = fields.Int(required=True)
    answers = fields.Nested("AnswerSchema", many=True, required=True)

    @pre_load
    def check_answers(self, data: dict, **kwargs) -> dict:
        if len(data.get('answers')) < 2 or len(
                # проверка на количество правильных ответов
                [i.get('is_correct') for i in data.get('answers') if
                 i.get('is_correct') is True]) != 1:
            raise HTTPBadRequest()
        return data



class AnswerSchema(Schema):
    title = fields.Str(required=True)
    is_correct = fields.Bool(required=True)


class ThemeListSchema(Schema):
    themes = fields.Nested(ThemeSchema, many=True)


class ThemeIdSchema(Schema):
    theme_id = fields.Int()


class ListQuestionSchema(Schema):
    questions = fields.Nested(QuestionSchema, many=True)
