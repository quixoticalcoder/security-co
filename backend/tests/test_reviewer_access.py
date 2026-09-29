import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.responses import StreamingResponse

from config import get_settings
from hosted_auth import COOKIE, HostedSessionMiddleware, owner, router, sign
from history import get_run, list_runs, owns_report, record_run

HEADERS = {'X-Security-Request':'1'}

@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setenv('SECURITY_CO_ACCESS_PASSWORD', 'test-only-owner-password')
    monkeypatch.setenv('HISTORY_DB_PATH', str(tmp_path / 'history.db'))
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(router)
    @app.get('/runs')
    async def runs():
        return list_runs()
    @app.get('/runs/{run_id}')
    async def detail(run_id: str):
        from fastapi.responses import JSONResponse
        result = get_run(run_id)
        return result if result else JSONResponse({}, status_code=404)
    @app.post('/check-email')
    async def email():
        return {'run_id':record_run('email','test email',[],{'label':'safe'},'/tmp/example.md')}
    @app.post('/check-links-stream')
    async def stream():
        async def events():
            await asyncio.sleep(0)
            run_id = record_run('link','https://example.com',[],{'label':'safe'},'/tmp/stream.md')
            yield json.dumps({'run_id':run_id})
        return StreamingResponse(events())
    @app.get('/reports/{filename}')
    async def report(filename: str):
        return {'report':filename}
    app.add_middleware(HostedSessionMiddleware)
    yield app
    get_settings.cache_clear()


def reviewer(app):
    client = TestClient(app, base_url='https://testserver')
    assert client.post('/session/reviewer', headers=HEADERS).status_code==200
    return client


def test_guest_scans_and_history_isolation(app):
    one, two = reviewer(app), reviewer(app)
    result=one.post('/check-email',headers=HEADERS,json={'text':'test email'})
    assert result.status_code==200
    run_id=result.json()['run_id']
    assert len(one.get('/runs').json())==1
    assert two.get('/runs').json()==[]
    assert two.get('/runs/'+run_id).status_code==404
    assert one.get('/reports/example.md').status_code==200
    assert two.get('/reports/example.md').status_code==404


def test_stream_retains_ownership(app):
    one, two = reviewer(app), reviewer(app)
    result=one.post('/check-links-stream',headers=HEADERS,json={'urls':['https://example.com']})
    assert result.status_code==200
    assert one.get('/runs/'+result.json()['run_id']).status_code==200
    assert two.get('/runs').json()==[]
    assert owner.get()=='owner'


def test_authentication_and_csrf(app):
    client=TestClient(app,base_url='https://testserver')
    assert client.get('/runs').status_code==401
    assert client.post('/session/reviewer').status_code==403
    assert client.post('/session/login',headers=HEADERS,json={'password':'wrong'}).status_code==401
    assert client.post('/session/login',headers=HEADERS,json={'password':'test-only-owner-password'}).status_code==200
    assert client.get('/session').json()['role']=='owner'
    assert client.post('/session/logout',headers=HEADERS).status_code==200
    assert client.get('/runs').status_code==401


def test_forged_expired_cookie_and_bounds(app):
    client=reviewer(app)
    token=client.cookies.get(COOKIE)
    client.cookies.clear()
    client.cookies.set(COOKIE,token[:-1]+('0' if token[-1]!='0' else '1'))
    assert client.get('/runs').status_code==401
    client.cookies.set(COOKIE,sign({'id':'owner','role':'owner','exp':time.time()-1}))
    assert client.get('/runs').status_code==401
    client=reviewer(app)
    assert client.post('/check-links-stream',headers=HEADERS,json={'urls':[]}).status_code==422
    assert client.post('/check-email',headers=HEADERS,content=b'x'*100001).status_code==413


def test_reviewer_daily_limit(app):
    client=reviewer(app)
    for _ in range(10):
        assert client.post('/check-email',headers=HEADERS,json={'text':'test'}).status_code==200
    assert client.post('/check-email',headers=HEADERS,json={'text':'test'}).status_code==429
