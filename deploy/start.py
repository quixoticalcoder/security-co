"""Supervise the loopback API and public dashboard in one container."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
children = []

def stop(*_):
    for child in children:
        if child.poll() is None:
            child.terminate()
    for child in children:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
    sys.exit(0)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
children.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api.app:app', '--host', '127.0.0.1', '--port', '8010'], cwd=root / 'backend'))
children.append(subprocess.Popen(['node', 'server.js'], cwd=root / 'dashboard', env=os.environ.copy()))
while all(child.poll() is None for child in children):
    time.sleep(1)
stop()
