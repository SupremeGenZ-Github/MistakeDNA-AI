import json
import math
import re
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete, func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from .config import settings
from .db import get_db, engine
from .models import User, AuthSession, Profile, QuizSession, Attempt, RateEvent
from .security import COOKIE, now, digest, hash_password, check_password, DUMMY_HASH, current_user, new_session, rate_limit
from .schemas import Credentials, LearningInput, ProfileInput, StartInput, AnswerInput, ReportInput, DeleteInput, TutorInput
from .engine import QUESTIONS, SKILLS, BY_ID, public_question, grade, trace, select_questions
from .tutor import offline_reply
from starlette.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app):
    settings.validate()
    yield

app=FastAPI(title='MistakeDNA AI',version='1.1.0',lifespan=lifespan,docs_url=None if settings.production else '/docs',redoc_url=None)

@app.middleware('http')
async def protect(request: Request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS') and request.url.path.startswith('/api/'):
        allowed={settings.app_origin}
        if not settings.production:
            allowed.update({'http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000'})
        if request.headers.get('origin') and request.headers['origin'].rstrip('/') not in allowed:
            return JSONResponse({'error':'Request origin is not allowed. Check APP_ORIGIN.'},status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site' or request.headers.get('x-mistakedna-request')!='1':
            return JSONResponse({'error':'Invalid request. Refresh this page and try again.'},status_code=403)
        try:
            length=int(request.headers.get('content-length','0'))
        except ValueError:
            return JSONResponse({'error':'Invalid request size.'},status_code=400)
        if length>32768:
            return JSONResponse({'error':'Request is too large.'},status_code=413)
        # Bounded streaming read also covers requests without Content-Length.
        chunks=[];size=0
        async for chunk in request.stream():
            size+=len(chunk)
            if size>32768:
                return JSONResponse({'error':'Request is too large.'},status_code=413)
            chunks.append(chunk)
        request._body=b''.join(chunks)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    if settings.production:
        response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    return response

@app.exception_handler(HTTPException)
async def http_error(_,exc):
    return JSONResponse({'error':exc.detail},status_code=exc.status_code,headers=exc.headers)

@app.exception_handler(RequestValidationError)
async def validation_error(_,exc):
    # Do not echo input (especially passwords) into validation responses/logs.
    return JSONResponse({'error':'Check your input. Use a valid email, a 12–128 character password and valid learning fields.'},status_code=422)

@app.exception_handler(SQLAlchemyError)
async def database_error(_,exc):
    # Avoid SQL parameters/connection strings in user-facing errors.
    return JSONResponse({'error':'The database request could not be completed. Please retry.'},status_code=503)

def attempts_for(db,uid):
    return list(db.scalars(select(Attempt).where(Attempt.user_id==uid).order_by(Attempt.created_at,Attempt.id)))

def profile_json(p):
    return None if not p else {'name':p.name,'grade':p.grade,'curriculum':p.curriculum,'subject':p.subject,'goal':p.goal,'createdAt':p.created_at}

def attempt_json(a):
    return {'id':a.id,'sessionId':a.session_id,'questionId':a.question_id,'answer':a.answer,'correct':a.correct,'skill':a.skill,'masteryBefore':a.mastery_before,'masteryAfter':a.mastery_after,'hypothesis':a.hypothesis,'reported':a.reported,'createdAt':a.created_at}

def feedback(a,q):
    return {'attempt':attempt_json(a),'explanation':q['explanation'],'correctAnswer':q['options'][int(q['answer'])] if q['type']=='mcq' else q['answer']}

@app.get('/api/health')
def health(db:Session=Depends(get_db)):
    try:
        db.execute(text('SELECT 1 FROM alembic_version'))
        return {'status':'ok'}
    except SQLAlchemyError:
        raise HTTPException(503,'Database is unavailable or migrations are missing.') from None

@app.get('/api/curriculum')
def curriculum():
    return {'skills':SKILLS,'questionCount':len(QUESTIONS)}

def auth_limits(request,db,email):
    # Uvicorn trusts only its configured immediate proxy for X-Forwarded-For.
    address=request.client.host if request.client else 'unknown'
    rate_limit(db,'auth-ip:'+digest(address),30,900)
    rate_limit(db,'auth-email:'+digest(email),10,900)

@app.post('/api/auth/register',status_code=201)
def register(body:Credentials,request:Request,response:Response,db:Session=Depends(get_db)):
    if not settings.allow_registration:
        raise HTTPException(403,'Registration is currently closed.')
    auth_limits(request,db,body.email)
    if db.scalar(select(User).where(User.email==body.email)):
        raise HTTPException(409,'An account cannot be created with these details. Try signing in.')
    user=User(id=str(uuid.uuid4()),email=body.email,password_hash=hash_password(body.password),created_at=now())
    db.add(user)
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'An account cannot be created with these details.') from None
    new_session(db,user.id,response,settings)
    return {'ok':True}

@app.post('/api/auth/login')
def login(body:Credentials,request:Request,response:Response,db:Session=Depends(get_db)):
    auth_limits(request,db,body.email)
    user=db.scalar(select(User).where(User.email==body.email))
    valid=check_password(body.password,user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401,'Email or password is incorrect.')
    # Rotate this browser's existing token.
    old=request.cookies.get(COOKIE)
    if old: db.execute(delete(AuthSession).where(AuthSession.token_hash==digest(old)))
    new_session(db,user.id,response,settings)
    return {'ok':True}

@app.post('/api/auth/logout')
def logout(request:Request,response:Response,db:Session=Depends(get_db)):
    token=request.cookies.get(COOKIE)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash==digest(token)));db.commit()
    response.delete_cookie(COOKIE,path='/',secure=settings.secure_cookies,httponly=True,samesite='lax')
    return {'ok':True}

class DeleteAccount(BaseModel):
    password:str=Field(min_length=12,max_length=128)
    confirmation:str

@app.post('/api/auth/delete')
def delete_account(body:DeleteAccount,response:Response,user:User=Depends(current_user),db:Session=Depends(get_db)):
    rate_limit(db,'delete:'+user.id,5,900)
    if body.confirmation!='DELETE' or not check_password(body.password,user.password_hash):
        raise HTTPException(400,'Password or deletion confirmation is incorrect.')
    db.execute(delete(RateEvent).where(RateEvent.bucket.in_(['tutor:'+user.id,'delete:'+user.id])))
    db.delete(user);db.commit() # FK cascades remove private learning data and all sessions.
    response.delete_cookie(COOKIE,path='/',secure=settings.secure_cookies,httponly=True,samesite='lax')
    return {'ok':True}

@app.get('/api/learning')
def learning(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return {'profile':profile_json(db.get(Profile,user.id)),'history':[attempt_json(a) for a in attempts_for(db,user.id)],'skills':SKILLS,'questionCount':len(QUESTIONS),'identity':{'name':'Learner','email':user.email},'aiAvailable':settings.ai_available}

@app.post('/api/learning')
def mutate(body:LearningInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    uid=user.id
    # Serialize writes per learner on PostgreSQL, including simultaneous quiz sessions.
    db.execute(select(User).where(User.id==uid).with_for_update())
    if isinstance(body,ProfileInput):
        p=db.get(Profile,uid)
        if not p:
            p=Profile(user_id=uid,created_at=now(),curriculum='CBSE');db.add(p)
        p.name,p.grade,p.subject,p.goal=body.name,body.grade,body.subject,body.goal
        db.commit();return {'ok':True}
    if isinstance(body,DeleteInput):
        db.execute(delete(Attempt).where(Attempt.user_id==uid))
        db.execute(delete(QuizSession).where(QuizSession.user_id==uid))
        db.execute(delete(Profile).where(Profile.user_id==uid));db.commit()
        return {'ok':True}
    if isinstance(body,ReportInput):
        a=db.scalar(select(Attempt).where(Attempt.id==body.attemptId,Attempt.user_id==uid))
        if not a: raise HTTPException(404,'Learning evidence not found.')
        a.reported=1;db.commit();return {'ok':True}
    if not db.get(Profile,uid):
        raise HTTPException(409,'Create your learner profile first.')
    if isinstance(body,StartInput):
        # Bound abandoned session creation as well as expensive provider calls.
        recent_count=db.scalar(select(func.count()).select_from(QuizSession).where(QuizSession.user_id==uid,QuizSession.created_at>=now()[:10]))
        if recent_count>=100: raise HTTPException(429,'Daily assessment limit reached. Continue tomorrow.')
        count=db.scalar(select(func.count()).select_from(QuizSession).where(QuizSession.user_id==uid,QuizSession.subject==body.subject,QuizSession.mode==body.mode))
        selected=select_questions(body.subject,body.mode,attempts_for(db,uid),count)
        session=QuizSession(id=str(uuid.uuid4()),user_id=uid,subject=body.subject,mode=body.mode,question_ids=json.dumps([q['id'] for q in selected]),created_at=now())
        db.add(session);db.commit()
        return {'id':session.id,'questions':[public_question(q) for q in selected]}
    session=db.scalar(select(QuizSession).where(QuizSession.id==body.sessionId,QuizSession.user_id==uid))
    if not session: raise HTTPException(404,'Assessment not found.')
    ids=json.loads(session.question_ids)
    if body.questionId not in ids or body.questionId not in BY_ID:
        raise HTTPException(400,'Question does not belong to this assessment.')
    q=BY_ID[body.questionId]
    attempt_id=session.id+':'+q['id']
    old=db.get(Attempt,attempt_id)
    if old: return feedback(old,q)
    done=list(db.scalars(select(Attempt).where(Attempt.session_id==session.id,Attempt.user_id==uid)))
    if len(done)>=len(ids) or ids[len(done)]!=q['id']:
        raise HTTPException(409,'Answer the current question first.')
    answer=body.answer.strip()
    if q['type']=='mcq':
        if not re.fullmatch(r'\d',answer) or int(answer)>=len(q['options']):
            raise HTTPException(400,'Select a valid answer option.')
    else:
        try:
            if not answer or not math.isfinite(float(answer)): raise ValueError()
        except ValueError:
            raise HTTPException(400,'Enter a finite numerical answer.') from None
    history=[a for a in attempts_for(db,uid) if a.skill==q['skill']]
    prior=history[-1].mastery_after if history else .3
    correct=grade(q,answer)
    attempt=Attempt(id=attempt_id,user_id=uid,session_id=session.id,question_id=q['id'],answer=answer,correct=int(correct),skill=q['skill'],mastery_before=prior,mastery_after=trace(prior,correct,q['difficulty'],q['type']=='numerical'),hypothesis=None if correct else q['misconceptions'].get(answer,'Uncertain: more evidence is needed to explain this answer'),reported=0,created_at=now())
    db.add(attempt)
    try: db.commit()
    except IntegrityError:
        db.rollback();saved=db.get(Attempt,attempt_id)
        if saved: return feedback(saved,q)
        raise HTTPException(409,'Another submission is being saved. Retry.') from None
    return feedback(attempt,q)

@app.get('/api/model')
def model_info(user:User=Depends(current_user)):
    from .offline_model.runtime import get_model,ModelUnavailable
    if not settings.ai_available: raise HTTPException(503,'Offline model unavailable or disabled.')
    try: return get_model(settings.offline_model_dir).public_info()
    except ModelUnavailable as exc: raise HTTPException(503,str(exc)) from None

@app.post('/api/tutor')
async def tutor(body:TutorInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if not settings.ai_available:
        raise HTTPException(503,'Offline model unavailable or disabled. Quizzes still work.')
    rate_limit(db,'tutor:'+user.id,settings.tutor_limit,3600)
    # Copy this learner's bounded context before running CPU work. No external provider.
    attempts=attempts_for(db,user.id)
    return await run_in_threadpool(offline_reply,settings,body,attempts)

static=Path(settings.static_dir)
if static.is_dir():
    if (static/'assets').is_dir():
        app.mount('/assets',StaticFiles(directory=static/'assets'),name='assets')
    @app.get('/')
    def home():
        return FileResponse(static/'index.html')
    @app.get('/{path:path}')
    def spa(path:str):
        if path.startswith('api/'):
            raise HTTPException(404,'Endpoint not found.')
        return FileResponse(static/'index.html')
