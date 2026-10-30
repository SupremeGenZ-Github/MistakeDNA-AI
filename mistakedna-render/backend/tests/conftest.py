import sys
import os
from pathlib import Path
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from sqlalchemy import text
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.db import get_db,make_engine
from app.config import settings

@pytest.fixture
def clients(tmp_path,monkeypatch):
    url=os.getenv('TEST_DATABASE_URL') or 'sqlite:///'+str(tmp_path/'test.db')
    if os.getenv('TEST_DATABASE_URL'):
        assert make_url(url).database.endswith('_test'), 'Only a disposable *_test database may be reset.'
        from app.models import Base
        cleanup_engine=make_engine(url)
        Base.metadata.drop_all(cleanup_engine)
        with cleanup_engine.begin() as connection:
            connection.execute(text('DROP TABLE IF EXISTS alembic_version'))
        cleanup_engine.dispose()
    monkeypatch.setattr(settings,'database_url',url)
    monkeypatch.setattr(settings,'production',False)
    monkeypatch.setattr(settings,'secure_cookies',False)
    monkeypatch.setattr(settings,'app_origin','http://localhost:8000')
    monkeypatch.setattr(settings,'offline_ai_enabled',True)
    monkeypatch.setattr(settings,'tutor_limit',20)
    monkeypatch.setattr(settings,'allow_registration',True)
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    command.upgrade(cfg,'head')
    engine=make_engine(url)
    Session=sessionmaker(bind=engine,expire_on_commit=False)
    def db_override():
        with Session() as db: yield db
    app.dependency_overrides[get_db]=db_override
    with TestClient(app,headers={'X-MistakeDNA-Request':'1'}) as one,TestClient(app,headers={'X-MistakeDNA-Request':'1'}) as two:
        yield one,two,Session,engine
    app.dependency_overrides.clear()
    engine.dispose()

@pytest.fixture
def account(clients):
    client=clients[0]
    result=client.post('/api/auth/register',json={'email':'student@example.test','password':'strong-password-123'})
    assert result.status_code==201,result.text
    result=client.post('/api/learning',json={'action':'profile','name':'QA Learner','grade':11,'subject':'Chemistry','goal':'Understand equilibrium'})
    assert result.status_code==200,result.text
    return client
