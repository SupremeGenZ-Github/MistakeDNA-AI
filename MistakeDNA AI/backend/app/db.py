from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .config import settings

def normalize_url(value):
    if value.startswith('postgres://'):
        value = 'postgresql+psycopg://' + value[len('postgres://'):]
    elif value.startswith('postgresql://'):
        value = 'postgresql+psycopg://' + value[len('postgresql://'):]
    return value

def make_engine(url):
    url = normalize_url(url)
    if url.startswith('sqlite:///') and ':memory:' not in url:
        Path(url[len('sqlite:///'):]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False, 'timeout': 20}} if url.startswith('sqlite') else {'pool_size': 5, 'max_overflow': 5}))
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_options(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine

engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def get_db():
    with SessionLocal() as db:
        yield db
