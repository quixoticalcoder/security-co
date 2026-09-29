"""Signed hosted sessions and per-request history ownership. Local mode is unchanged."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextvars import ContextVar
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

from config import get_settings

owner = ContextVar('history_owner', default='owner')
COOKIE = 'security_session'
SCANS = {'/check-links', '/check-links-stream', '/check-email', '/check-email-stream'}
router = APIRouter()


def secret():
    return os.environ.get('SECURITY_CO_ACCESS_PASSWORD', '')


def sign(payload):
    value = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode().rstrip('=')
    signature = hmac.new(secret().encode(), value.encode(), hashlib.sha256).hexdigest()
    return value + '.' + signature


def verify(value):
    try:
        body, signature = value.split('.')
        expected = hmac.new(secret().encode(), body.encode(), hashlib.sha256).hexdigest()
        if not secret() or not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if payload['exp'] < time.time() or payload['role'] not in ('owner', 'reviewer'):
            return None
        if payload['role'] == 'owner' and payload['id'] != 'owner':
            return None
        if payload['role'] == 'reviewer' and (len(payload['id']) != 32 or any(c not in '0123456789abcdef' for c in payload['id'])):
            return None
        return payload
    except (ValueError, KeyError, TypeError):
        return None


def usage(key, maximum):
    path = Path(get_settings().HISTORY_DB_PATH).with_name('hosted_usage.db')
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS usage (key TEXT PRIMARY KEY, count INTEGER, reset REAL)')
        db.execute('BEGIN IMMEDIATE')
        now = time.time()
        db.execute('DELETE FROM usage WHERE reset < ?', (now,))
        row = db.execute('SELECT count FROM usage WHERE key=?', (key,)).fetchone()
        if row and row[0] >= maximum:
            return False
        db.execute('INSERT INTO usage VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1', (key, now+86400))
        return True


def session_response(role):
    payload = {'id': 'owner' if role == 'owner' else secrets.token_hex(16), 'role': role, 'exp': int(time.time())+86400}
    response = JSONResponse({'role': role})
    response.set_cookie(COOKIE, sign(payload), secure=True, httponly=True, samesite='strict', max_age=86400, path='/')
    response.headers['Cache-Control'] = 'no-store'
    return response


@router.post('/session/reviewer')
async def reviewer():
    if not secret():
        return JSONResponse({'detail': 'Hosted sign-in is not configured.'}, status_code=503)
    return session_response('reviewer')


@router.post('/session/login')
async def login(request: Request):
    if not secret():
        return JSONResponse({'detail': 'Hosted sign-in is not configured.'}, status_code=503)
    address = request.headers.get('x-forwarded-for', request.client.host if request.client else 'unknown')
    if not usage('login:'+hashlib.sha256(address.encode()).hexdigest(), 30):
        return JSONResponse({'detail': 'Too many login attempts. Please try again later.'}, status_code=429)
    data = await request.json()
    password = data.get('password', '') if isinstance(data, dict) else ''
    if not isinstance(password, str) or not hmac.compare_digest(hashlib.sha256(password.encode()).digest(), hashlib.sha256(secret().encode()).digest()):
        return JSONResponse({'detail': 'Incorrect password.'}, status_code=401)
    return session_response('owner')


@router.post('/session/logout')
async def logout():
    response = JSONResponse({'ok': True})
    response.delete_cookie(COOKIE, path='/')
    return response


@router.get('/session')
async def current(request: Request):
    payload = verify(request.cookies.get(COOKIE, ''))
    return {'role': payload['role'], 'expires_at': payload['exp']}


class HostedSessionMiddleware:
    """ASGI scope keeps ownership attached through streaming response completion."""
    def __init__(self, app):
        self.app = app
        self.active = 0

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        request = StarletteRequest(scope)
        path = scope['path']
        async def reject(status, detail):
            await JSONResponse({'detail': detail}, status_code=status, headers={'Cache-Control':'no-store'})(scope, receive, send)
        if path == '/health':
            return await self.app(scope, receive, send)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.headers.get('x-security-request') != '1':
            return await reject(403, 'Submit this request through Security Co.')
        if path in ('/session/login', '/session/reviewer', '/session/logout'):
            # Bound credential request size and malformed JSON handling.
            body = b''
            while True:
                message = await receive()
                if message['type'] == 'http.disconnect':
                    return
                body += message.get('body', b'')
                if len(body) > 8192:
                    return await reject(413, 'Request too large.')
                if not message.get('more_body', False):
                    break
            if path == '/session/login':
                try:
                    json.loads(body)
                except ValueError:
                    return await reject(422, 'Enter your password.')
            sent = False
            async def replay():
                nonlocal sent
                if not sent:
                    sent = True
                    return {'type':'http.request', 'body':body, 'more_body':False}
                return await receive()
            return await self.app(scope, replay, send)
        payload = verify(request.cookies.get(COOKIE, ''))
        if not payload:
            return await reject(401, 'Your session expired. Sign in or start a reviewer session.')
        token = owner.set(payload['id'])
        is_scan = path in SCANS and request.method == 'POST'
        counted = False
        try:
            if path.startswith('/screenshots/'):
                return await reject(404, 'Screenshots are unavailable in the hosted edition.')
            if path.startswith('/reports/'):
                from history import owns_report
                if not owns_report(path.removeprefix('/reports/')):
                    return await reject(404, 'Report not found.')
            if is_scan and payload['role'] == 'reviewer':
                body = b''
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    body += message.get('body', b'')
                    if len(body) > 100000:
                        return await reject(413, 'Please use an email or link request smaller than 100 KB.')
                    if not message.get('more_body', False):
                        break
                try:
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ValueError()
                    if 'links' in path:
                        urls = data.get('urls')
                        if not isinstance(urls, list) or len(urls) != 1 or not isinstance(urls[0], str) or not urls[0].strip():
                            raise ValueError()
                    elif not isinstance(data.get('text'), str) or not data['text'].strip():
                        raise ValueError()
                except ValueError:
                    return await reject(422, 'Enter one website URL or a non-empty email to investigate.')
                original_receive = receive
                sent = False
                async def replay_scan():
                    nonlocal sent
                    if not sent:
                        sent = True
                        return {'type':'http.request', 'body':body, 'more_body':False}
                    return await original_receive()
                receive = replay_scan
                if self.active >= 2:
                    return await reject(429, 'The demo is busy with two investigations. Please try again shortly.')
                if not usage('reviewer:'+payload['id'], 10):
                    return await reject(429, 'This reviewer session has used its 10 daily scans.')
                if not usage('reviewer-global', 40):
                    return await reject(429, 'The shared free reviewer allowance is exhausted. Please try tomorrow.')
                self.active += 1
                counted = True
            await self.app(scope, receive, send)
        finally:
            if counted:
                self.active -= 1
            owner.reset(token)
