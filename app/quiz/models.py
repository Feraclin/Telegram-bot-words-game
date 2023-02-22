from dataclasses import dataclass

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.database.sqlalchemy_base import DB


@dataclass
class Theme:
    id: int | None
    title: str


@dataclass
class Question:
    id: int | None
    title: str
    theme_id: int
    answers: list["Answer"]


@dataclass
class Answer:
    title: str
    is_correct: bool
    question_id: int | None = None


class ThemeModel(DB):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False, unique=True)
    questions_children: Mapped[list['QuestionModel']] = relationship(back_populates='theme_parent',
                                                                     cascade="all, delete-orphan",
                                                                     lazy='subquery')

    def to_dc(self) -> Theme:
        return Theme(id=self.id,
                     title=self.title)


class QuestionModel(DB):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False, unique=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey('themes.id', ondelete='CASCADE'), nullable=False)
    theme_parent: Mapped[ThemeModel] = relationship(back_populates="questions_children")
    answers: Mapped[list['AnswerModel']] = relationship(back_populates='question_parent',
                                                        cascade='all, delete',
                                                        lazy='subquery')

    def to_dc(self) -> Question:
        answers_list = [i.to_dc() for i in self.answers]
        return Question(id=self.id,
                        title=self.title,
                        theme_id=self.theme_id,
                        answers=answers_list)


class AnswerModel(DB):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    is_correct: Mapped[bool] = mapped_column(nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    question_parent: Mapped[QuestionModel] = relationship(back_populates='answers',
                                                          cascade='all, delete',
                                                          lazy='subquery')

    def to_dc(self) -> Answer:
        return Answer(title=self.title,
                      is_correct=self.is_correct)
