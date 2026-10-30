from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

Subject = Literal['Chemistry','Physics','Mathematics','Biology','Social Science']
class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value

class ProfileInput(BaseModel):
    action: Literal['profile']
    name: str = Field(min_length=1, max_length=60)
    grade: int = Field(ge=9, le=12)
    subject: Subject
    goal: str = Field(default='', max_length=240)
    @field_validator('name')
    @classmethod
    def clean_name(cls, value):
        if not value.strip(): raise ValueError('Enter your name.')
        return value.strip()

class StartInput(BaseModel):
    action: Literal['start']
    subject: Subject
    mode: Literal['diagnostic','practice']
    grade: int | None = Field(default=None,ge=9,le=12)
    chapterId: str | None = Field(default=None,max_length=240)

class AnswerInput(BaseModel):
    action: Literal['answer']
    sessionId: str = Field(min_length=36,max_length=36)
    questionId: str = Field(max_length=20)
    answer: str = Field(min_length=1,max_length=120)

class ReportInput(BaseModel):
    action: Literal['report']
    attemptId: str = Field(max_length=100)

class DeleteInput(BaseModel):
    action: Literal['delete']
    confirmation: Literal['DELETE']

LearningInput = Annotated[Union[ProfileInput, StartInput, AnswerInput, ReportInput, DeleteInput], Field(discriminator='action')]

class TutorInput(BaseModel):
    subject: Subject
    grade: int | None = Field(default=None,ge=9,le=12)
    chapterId: str | None = Field(default=None,max_length=240)
    message: str = Field(min_length=1, max_length=1500)
    history: list[dict[str,str]] = Field(default_factory=list, max_length=6)
    @field_validator('history')
    @classmethod
    def bounded_history(cls, messages):
        for m in messages:
            if m.get('role') not in ('user','assistant') or len(m.get('content',''))>3000:
                raise ValueError('Invalid conversation history.')
        return [{'role':m['role'],'content':m['content']} for m in messages]
