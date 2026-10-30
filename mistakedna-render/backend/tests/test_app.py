import json
import pytest
import httpx
from sqlalchemy import select,func
from app.models import User,AuthSession,Attempt,Profile,QuizSession
from app.security import hash_password,check_password,COOKIE
from app.engine import QUESTIONS,SKILLS,BY_ID,grade,trace,public_question,select_questions
from app.db import normalize_url
from app.config import settings

CREDS={'email':'student@example.test','password':'strong-password-123'}
def register(client,email='student@example.test'):
    return client.post('/api/auth/register',json={**CREDS,'email':email})
def start(client,mode='diagnostic',subject='Chemistry'):
    r=client.post('/api/learning',json={'action':'start','subject':subject,'mode':mode,'grade':11 if subject=='Chemistry' else 10,'chapterId':next(c['id'] for c in __import__('app.engine',fromlist=['CATALOG']).CATALOG['chapters'] if c['grade']==(11 if subject=='Chemistry' else 10) and c['subject']==subject and c['title']==('Equilibrium' if subject=='Chemistry' else 'Quadratic Equations'))})
    assert r.status_code==200,r.text
    return r.json()
def answer(client,session,q,value=None):
    return client.post('/api/learning',json={'action':'answer','sessionId':session['id'],'questionId':q['id'],'answer':BY_ID[q['id']]['answer'] if value is None else value})

def test_auth_passwords_login_logout_and_no_identity_header_bypass(clients):
    one,two,Session,_=clients
    assert one.get('/api/learning').status_code==401
    assert one.get('/api/learning',headers={'oai-authenticated-user-id':'pretend','oai-authenticated-user-email':'fake@test.test'}).status_code==401
    assert register(one).status_code==201
    assert one.get('/api/learning').status_code==200
    assert one.cookies.get(COOKIE)
    with Session() as db:
        user=db.scalar(select(User));assert user.password_hash!=CREDS['password'];assert check_password(CREDS['password'],user.password_hash)
        token=db.scalar(select(AuthSession));assert token.token_hash!=one.cookies.get(COOKIE)
    assert two.post('/api/auth/login',json={**CREDS,'password':'incorrect-password'}).status_code==401
    assert two.post('/api/auth/login',json=CREDS).status_code==200
    assert one.post('/api/auth/logout',json={}).status_code==200
    assert one.get('/api/learning').status_code==401
    assert two.get('/api/learning').status_code==200

def test_registration_validation_and_no_password_echo(clients):
    c=clients[0]
    r=c.post('/api/auth/register',json={'email':'wrong','password':'short'})
    assert r.status_code==422
    assert 'short' not in r.text
    assert register(c).status_code==201
    assert register(c).status_code==409
    assert c.post('/api/learning',json={'action':'profile','name':' ','grade':99,'subject':'invalid'}).status_code==422

def test_complete_diagnostic_practice_retest_persistence_and_reports(account,clients):
    c=account
    s=start(c)
    assert len(s['questions'])==10
    assert len({q['skill'] for q in s['questions']})==5
    assert answer(c,s,s['questions'][1]).status_code==409
    assert answer(c,s,s['questions'][0],'999').status_code==400
    first=answer(c,s,s['questions'][0],'0');assert first.status_code==200
    duplicate=answer(c,s,s['questions'][0],'1');assert duplicate.json()==first.json()
    for q in s['questions'][1:]: assert answer(c,s,q).status_code==200
    saved=c.get('/api/learning').json();assert len(saved['history'])==10
    assert len({h['skill'] for h in saved['history']})==5
    assert all(h['masteryBefore']!=h['masteryAfter'] for h in saved['history'])
    # Reconnect the file-backed database and sign in from a new browser client.
    clients[3].dispose()
    other=clients[1]
    assert other.post('/api/auth/login',json=CREDS).status_code==200
    assert other.get('/api/learning').json()['history']==saved['history']
    practice=start(c,'practice');assert len(practice['questions'])==5
    for q in practice['questions']: assert answer(c,practice,q).status_code==200
    retest=start(c);assert [q['id'] for q in retest['questions']]!=[q['id'] for q in s['questions']]
    assert len(c.get('/api/learning').json()['history'])==15
    assert c.get('/api/health').json()=={'status':'ok'}

def test_cross_user_isolation_flags_and_deletion(account,clients):
    a=account;b=clients[1]
    assert register(b,'other@example.test').status_code==201
    assert b.post('/api/learning',json={'action':'profile','name':'Other','grade':10,'subject':'Mathematics'}).status_code==200
    s=start(a);q=s['questions'][0];result=answer(a,s,q,'0').json()
    assert answer(b,s,q).status_code==404
    assert b.post('/api/learning',json={'action':'report','attemptId':result['attempt']['id']}).status_code==404
    assert b.get('/api/learning').json()['history']==[]
    assert a.post('/api/learning',json={'action':'report','attemptId':result['attempt']['id']}).status_code==200
    assert a.get('/api/learning').json()['history'][0]['reported']==1
    assert a.post('/api/learning',json={'action':'delete','confirmation':'DELETE'}).status_code==200
    assert a.get('/api/learning').json()['profile'] is None
    assert a.get('/api/learning').json()['history']==[]
    assert b.get('/api/learning').json()['profile']['name']=='Other'

def test_permanent_account_deletion_revokes_other_sessions(account,clients):
    a=account;b=clients[1];s=start(a);answer(a,s,s['questions'][0])
    assert b.post('/api/auth/login',json=CREDS).status_code==200
    assert a.post('/api/auth/delete',json={'password':'wrong-password-123','confirmation':'DELETE'}).status_code==400
    assert a.post('/api/auth/delete',json={'password':CREDS['password'],'confirmation':'DELETE'}).status_code==200
    assert b.get('/api/learning').status_code==401
    with clients[2]() as db:
        for model in (User,AuthSession,Profile,QuizSession,Attempt):
            assert db.scalar(select(func.count()).select_from(model))==0

def test_csrf_headers_origin_size_and_expired_sessions(account,clients):
    c=account
    assert c.post('/api/learning',json={'action':'delete','confirmation':'DELETE'},headers={'Origin':'https://attacker.test'}).status_code==403
    assert c.post('/api/auth/logout',json={},headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    headers=dict(c.headers);c.headers.pop('X-MistakeDNA-Request')
    assert c.post('/api/auth/logout',json={}).status_code==403
    c.headers.update(headers)
    assert c.post('/api/learning',content='x'*33000).status_code==413
    with clients[2]() as db:
        token=db.scalar(select(AuthSession));token.expires_at='2000-01-01T00:00:00.000000+00:00';db.commit()
    assert c.get('/api/learning').status_code==401

def test_cookie_security_and_registration_switch(clients,monkeypatch):
    c=clients[0];monkeypatch.setattr(settings,'secure_cookies',True)
    r=register(c);assert r.status_code==201
    cookie=r.headers['set-cookie'].lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=lax' in cookie
    monkeypatch.setattr(settings,'allow_registration',False)
    assert register(clients[1],'new@example.test').status_code==403

def test_auth_rate_limit(clients):
    c=clients[0]
    for _ in range(10): assert c.post('/api/auth/login',json=CREDS).status_code==401
    assert c.post('/api/auth/login',json=CREDS).status_code==429

def test_tutor_disabled_unauthorized_and_no_external_fallback(account,clients,monkeypatch):
    body={'subject':'Chemistry','message':'Explain Kp and Kc'}
    assert clients[1].post('/api/tutor',json=body).status_code==401
    monkeypatch.setattr(settings,'offline_ai_enabled',False)
    r=account.post('/api/tutor',json=body)
    assert r.status_code==503 and 'reply' not in r.json()

def test_custom_model_runs_without_network_and_uses_actual_evidence(account,monkeypatch):
    import socket
    def no_network(*args,**kwargs):raise AssertionError('Offline inference attempted a network call')
    monkeypatch.setattr(socket,'create_connection',no_network)
    monkeypatch.setattr(httpx,'AsyncClient',no_network)
    s=start(account)
    for q in s['questions']:
        assert answer(account,s,q,'0').status_code==200
    monkeypatch.setattr(settings,'tutor_limit',2)
    info=account.get('/api/model').json()
    assert info['pretrained'] is False and info['parameters']==137984
    r=account.post('/api/tutor',json={'subject':'Chemistry','message':'Explain Kp and Kc'})
    assert r.status_code==200,r.text
    data=r.json();assert data['engine']=='custom_tinylm'
    assert 'gaseous product coefficients minus' in data['reply'].lower()
    assert data['evidence'] and 'does not establish' in data['evidence']['note']
    assert 'student@example.test' not in r.text
    r=account.post('/api/tutor',json={'subject':'Chemistry','message':'Explain again more simply','history':[{'role':'user','content':'Explain Kp and Kc'}]})
    assert r.status_code==200 and r.json()['mode']=='simple'
    assert account.post('/api/tutor',json={'subject':'Chemistry','message':'Explain Kp'}).status_code==429
    assert len(account.get('/api/learning').json()['history'])==10

def test_scope_and_subject_boundaries(account):
    for subject,message in [('Chemistry','Write a poem about Mars'),('Mathematics','Explain Kp')]:
        r=account.post('/api/tutor',json={'subject':subject,'message':message})
        assert r.status_code==200 and r.json()['engine']=='scope_message'
    r=account.post('/api/tutor',json={'subject':'Mathematics','message':'Give me a hint about the discriminant'})
    assert r.status_code==200 and r.json()['engine']=='custom_tinylm' and r.json()['mode']=='hint'

def test_missing_or_corrupt_model_fails_cleanly(account,monkeypatch,tmp_path):
    monkeypatch.setattr(settings,'offline_model_dir',str(tmp_path))
    assert account.post('/api/tutor',json={'subject':'Chemistry','message':'Explain Kp'}).status_code==503
    from app.offline_model.runtime import TinyLM,ModelUnavailable
    with pytest.raises(ModelUnavailable):TinyLM(tmp_path)

def test_content_grading_graph_and_mastery():
    assert len(QUESTIONS)>=104 and len(BY_ID)==len(QUESTIONS)
    for q in QUESTIONS:
        assert grade(q,q['answer'])
        assert q['explanation'] and q['hint']
        assert all(k not in public_question(q) for k in ('answer','explanation','misconceptions'))
        for a in q['misconceptions']:
            assert a!=q['answer'] and q['options'][int(a)]
        if q['type']=='mcq':
            for i in range(len(q['options'])):assert grade(q,str(i))==(str(i)==q['answer'])
    q=BY_ID['m12']
    for invalid in ('',' ','nan','inf','word','4.1'):assert not grade(q,invalid)
    assert grade(q,'4.0000001')
    assert trace(.3,True,2)>.3 and trace(.8,False,2)<.8
    for p in (.005,.3,.8,.995):
        for correct in (True,False):
            for d in (1,2,3):assert .005<=trace(p,correct,d)<=.995
    def visit(s,path=()):
        assert s['id'] not in path
        for p in s['prerequisites']:visit(next(x for x in SKILLS if x['id']==p),(*path,s['id']))
    for s in SKILLS:visit(s)
    assert normalize_url('postgres://user:pass@host/db').startswith('postgresql+psycopg://')

def test_production_requires_postgres_https_and_secure_cookies(monkeypatch):
    monkeypatch.setattr(settings,'production',True)
    monkeypatch.setattr(settings,'database_url','sqlite:///discard.db')
    with pytest.raises(RuntimeError): settings.validate()
    monkeypatch.setattr(settings,'database_url','postgresql://u:p@host/db')
    monkeypatch.setattr(settings,'app_origin','http://unsafe.test')
    with pytest.raises(RuntimeError): settings.validate()

def test_render_environment_variable_loading(tmp_path):
    import os,subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    env={**os.environ,'PYTHONPATH':str(root/'backend'),'APP_ENV':'production','COOKIE_SECURE':'true','DATABASE_URL':'postgresql://test:test@database/mistakedna','RENDER_EXTERNAL_URL':'https://example.onrender.com','OFFLINE_AI_ENABLED':'true'}
    env.pop('APP_ORIGIN',None)
    command="from app.config import settings; settings.validate(); assert settings.app_origin=='https://example.onrender.com'; assert settings.ai_available; from app.db import normalize_url; assert normalize_url(settings.database_url).startswith('postgresql+psycopg://')"
    result=subprocess.run([sys.executable,'-c',command],env=env,cwd=root,capture_output=True,text=True)
    assert result.returncode==0,result.stderr

def test_built_frontend_is_served_with_assets(clients):
    import re
    c=clients[0]
    page=c.get('/')
    if page.status_code==404: pytest.skip('Run npm run build --prefix frontend before static asset verification.')
    assert page.status_code==200 and 'id="root"' in page.text
    script=re.search(r'src="([^"]+\.js)"',page.text).group(1)
    asset=c.get(script);assert asset.status_code==200
    assert 'At chemical equilibrium in a closed system' not in asset.text
    assert 'mistakedna_session' not in asset.text
    assert c.get('/api/not-a-real-endpoint').status_code==404
    assert c.get('/api/curriculum').status_code==200
