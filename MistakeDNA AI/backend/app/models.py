from sqlalchemy import String, Integer, Float, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[str] = mapped_column(String(32))

class AuthSession(Base):
    __tablename__ = 'auth_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[str] = mapped_column(String(32), index=True)

class Profile(Base):
    __tablename__ = 'profiles'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    grade: Mapped[int] = mapped_column(Integer)
    curriculum: Mapped[str] = mapped_column(String(30), default='CBSE')
    subject: Mapped[str] = mapped_column(String(30))
    goal: Mapped[str] = mapped_column(String(240), default='')
    created_at: Mapped[str] = mapped_column(String(32))

class QuizSession(Base):
    __tablename__ = 'quiz_sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    subject: Mapped[str] = mapped_column(String(30))
    mode: Mapped[str] = mapped_column(String(20))
    question_ids: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))

class Attempt(Base):
    __tablename__ = 'attempts'
    __table_args__ = (UniqueConstraint('session_id', 'question_id', name='uq_session_question'), Index('ix_attempt_owner_skill', 'user_id', 'skill'))
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('quiz_sessions.id', ondelete='CASCADE'), index=True)
    question_id: Mapped[str] = mapped_column(String(20))
    answer: Mapped[str] = mapped_column(String(120))
    correct: Mapped[int] = mapped_column(Integer)
    skill: Mapped[str] = mapped_column(String(30))
    mastery_before: Mapped[float] = mapped_column(Float)
    mastery_after: Mapped[float] = mapped_column(Float)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(32))

class RateEvent(Base):
    __tablename__ = 'rate_events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(100), index=True)
    at: Mapped[str] = mapped_column(String(32), index=True)
