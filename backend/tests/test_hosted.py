import asyncio
import socket
import pytest
from fastapi.testclient import TestClient
from config import get_settings
from tools.inspect_http import public_target

@pytest.mark.parametrize('url', ['file:///etc/passwd','http://127.0.0.1','http://[::1]','http://169.254.169.254','http://user:pass@example.com','https://example.com:8080'])
def test_rejects_unsafe_targets(url):
    with pytest.raises(ValueError):
        public_target(url)

def test_pins_resolved_address(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(2,1,6,'',('93.184.216.34',443))])
    target, host, port = public_target('https://example.com/path?q=1')
    assert target == 'https://93.184.216.34:443/path?q=1'
    assert host == 'example.com'

def test_hosted_health_and_disabled_features(monkeypatch):
    monkeypatch.setenv('HOSTED_LITE','true')
    get_settings.cache_clear()
    from api.app import create_app
    with TestClient(create_app()) as client:
        assert client.get('/health').status_code == 200
        assert client.post('/report-flow', json={}).status_code == 503
        assert client.post('/quick-check', json={}).status_code == 503
