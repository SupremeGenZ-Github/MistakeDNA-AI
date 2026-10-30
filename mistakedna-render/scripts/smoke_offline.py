"""Real local HTTP smoke test with a disposable SQLite file. No external services."""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as work:
    env={**os.environ,'APP_ENV':'development','COOKIE_SECURE':'false','APP_ORIGIN':'http://localhost:8000','DATABASE_URL':'sqlite:///'+str(Path(work)/'smoke.db'),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','OFFLINE_AI_ENABLED':'true'}
    subprocess.run([sys.executable,'-m','alembic','-c','backend/alembic.ini','upgrade','head'],env=env,cwd=ROOT,check=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    process=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',headers={'X-MistakeDNA-Request':'1'},trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.ConnectError:pass
                time.sleep(.1)
            else:raise RuntimeError('Server did not become ready')
            assert client.get('/').status_code==200,'Build the frontend before this smoke test.'
            credentials={'email':'disposable@example.test','password':'disposable-test-password-123'}
            assert client.post('/api/auth/register',json=credentials).status_code==201
            assert client.post('/api/learning',json={'action':'profile','name':'Disposable QA','grade':11,'subject':'Chemistry'}).status_code==200
            session=client.post('/api/learning',json={'action':'start','subject':'Chemistry','mode':'diagnostic'}).json()
            for q in session['questions']:
                assert client.post('/api/learning',json={'action':'answer','sessionId':session['id'],'questionId':q['id'],'answer':'0'}).status_code==200
            result=client.post('/api/tutor',json={'subject':'Chemistry','message':'Explain Kp and Kc'});assert result.status_code==200,result.text
            assert result.json()['engine']=='custom_tinylm'
            assert client.post('/api/auth/logout',json={}).status_code==200
            assert client.post('/api/auth/login',json=credentials).status_code==200
            assert len(client.get('/api/learning').json()['history'])==10
            report=client.get('/api/report?format=pdf')
            assert report.status_code==200 and report.content.startswith(b'%PDF')
            assert report.headers['cache-control']=='no-store'
            assert 'Recorded answers: 10' in client.get('/api/report?format=md').text
            assert client.post('/api/auth/delete',json={'password':credentials['password'],'confirmation':'DELETE'}).status_code==200
            assert client.get('/api/learning').status_code==401
            print('PASS: frontend, account, ten diagnostic answers, actual offline neural generation, logout/login persistence, private PDF/Markdown downloads, deletion.')
    finally:
        process.terminate();process.wait(timeout=10)
