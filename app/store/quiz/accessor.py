from sqlalchemy import insert, select

from app.base.base_accessor import BaseAccessor
from app.quiz.models import (
    Answer,
    Question,
    ThemeModel,
    QuestionModel,
    AnswerModel
)


class QuizAccessor(BaseAccessor):
    async def create_theme(self, title: str | list[str]) -> ThemeModel | list[ThemeModel]:
        res = await self.app.database.scalars_query(insert(ThemeModel).returning(ThemeModel),
                                                    [{'title': title}] if type(title) is str else [{'title': i} for i in
                                                                                                   title])
        return res.one().to_dc()

    async def get_theme_by_title(self, title: str) -> ThemeModel | None:
        res = await self.app.database.execute_query(select(ThemeModel).where(ThemeModel.title == title))
        return res.scalar().to_dc()

    async def get_theme_by_id(self, id_: int) -> ThemeModel | None:
        res = await self.app.database.execute_query(select(ThemeModel).where(ThemeModel.id == id_))
        return res.scalar().to_dc()

    async def list_themes(self) -> list[ThemeModel]:
        res = await self.app.database.execute_query(select(ThemeModel))
        return [i.to_dc() for i in res.scalars()]

    async def create_answers(self,
                             question_id: int,
                             answers: list[Answer]) -> list[AnswerModel]:
        res = await self.app.database.scalars_query(insert(AnswerModel).returning(AnswerModel),
                                                    [{'question_id': question_id,
                                                      'title': answer.title,
                                                      'is_correct': answer.is_correct}
                                                     for answer in answers])
        return res.all()

    async def create_question(self,
                              title: str,
                              theme_id: int,
                              answers: list[Answer]) -> QuestionModel:
        res = await self.app.database.scalars_query(insert(QuestionModel).returning(QuestionModel.id),
                                                    [{'title': title, 'theme_id': theme_id}])

        question_id = res.one()

        await self.app.store.quizzes.create_answers(question_id, answers)

        return (await self.app.database.execute_query(
            select(QuestionModel).where(QuestionModel.id == question_id))).scalar().to_dc()

    async def get_question_by_title(self, title: str) -> QuestionModel | None:
        res = await self.app.database.execute_query(select(QuestionModel).where(QuestionModel.title == title))
        question = res.scalar().to_dc()
        print(question)
        return question

    async def list_questions(self, theme_id: int | None = None) -> list[Question]:
        if theme_id:
            res = await self.app.database.execute_query(select(QuestionModel).where(QuestionModel.theme_id == theme_id))
        else:
            res = await self.app.database.execute_query(select(QuestionModel))
        return [question.to_dc() for question in res.scalars()]
