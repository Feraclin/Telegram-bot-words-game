from aiohttp.web_exceptions import HTTPConflict, HTTPNotFound
from aiohttp_apispec import querystring_schema, request_schema, response_schema, docs
from sqlalchemy import select

from app.quiz.models import ThemeModel, AnswerModel
from app.quiz.schemes import (
    ListQuestionSchema,
    QuestionSchema,
    ThemeIdSchema,
    ThemeListSchema,
    ThemeSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class ThemeAddView(AuthRequiredMixin, View):
    @docs(tags=["quiz_accessor"], summary="Adding Theme", description="Add a new theme if it not exists")
    @request_schema(ThemeSchema)
    @response_schema(ThemeSchema)
    async def post(self):
        title = (await self.request.json())["title"]
        query = select(ThemeModel.title).where(ThemeModel.title == title)
        res = await self.request.app.database.execute_query(query)
        if res.fetchone():
            raise HTTPConflict()
        theme = await self.store.quizzes.create_theme(title)

        self.request.app.logger.info(f"added theme: {theme} successful")
        return json_response(data=ThemeSchema().dump(theme))


class ThemeListView(AuthRequiredMixin, View):
    @docs(tags=["quiz_accessor"], summary="Theme's list", description="Returns a list of themes")
    @response_schema(ThemeListSchema)
    async def get(self):
        themes = [ThemeSchema().dump(theme) for theme in await self.store.quizzes.list_themes()]
        return json_response(data={'themes': themes})


class QuestionAddView(AuthRequiredMixin, View):
    @request_schema(QuestionSchema)
    @response_schema(QuestionSchema)
    async def post(self):
        quest = await self.request.json()

        if not await self.store.quizzes.get_theme_by_id(quest.get('theme_id')):
            raise HTTPNotFound()

        question = await self.store.quizzes.create_question(title=quest.get('title'),
                                                            theme_id=quest.get('theme_id'),
                                                            answers=[
                                                                AnswerModel(title=i.get('title'),
                                                                            is_correct=i.get(
                                                                                'is_correct')) for i in
                                                                quest.get('answers')])
        self.request.app.logger.info(f"added theme: {question.title} successful")
        return json_response(data=QuestionSchema().dump(question))


class QuestionListView(AuthRequiredMixin, View):
    @docs(tags=["quiz_accessor"], summary="Question's list", description="Returns a list of all questions")
    @querystring_schema(ThemeIdSchema)
    @response_schema(ListQuestionSchema)
    async def get(self):
        try:
            theme_id = self.request.query.get("theme_id", None)
            questions_lst = await self.store.quizzes.list_questions(theme_id=int(theme_id))
        except:
            questions_lst = await self.store.quizzes.list_questions()
        questions = [QuestionSchema().dump(i) for i in questions_lst]
        return json_response(data={'questions': questions})
