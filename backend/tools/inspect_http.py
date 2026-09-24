"""Bounded HTTP-only inspection for the low-memory hosted edition."""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit, urljoin

import httpx
from bs4 import BeautifulSoup


def public_target(url):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('Only public HTTP(S) URLs without credentials are allowed.')
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    if port not in {80, 443}:
        raise ValueError('Only ports 80 and 443 are available in hosted mode.')
    addresses = {r[4][0] for r in socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
        raise ValueError('Private, loopback and reserved network addresses are not allowed.')
    address = sorted(addresses)[0]
    netloc = f'[{address}]' if ':' in address else address
    return urlunsplit((parts.scheme, f'{netloc}:{port}', parts.path or '/', parts.query, '')), parts.hostname, port


async def inspect_http(url):
    try:
        chain = []
        async with httpx.AsyncClient(timeout=12, trust_env=False) as client:
            for _ in range(6):
                target, hostname, port = await asyncio.to_thread(public_target, url)
                # Connect to the validated address; retain Host and TLS SNI.
                async with client.stream('GET', target, headers={'Host': hostname, 'User-Agent': 'Security-Co/1.0'}, extensions={'sni_hostname': hostname}) as response:
                    chain.append({'url': url, 'status': response.status_code})
                    if response.is_redirect:
                        location = response.headers.get('location')
                        if not location:
                            raise ValueError('Redirect has no destination.')
                        url = urljoin(url, location)
                        continue
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 256_000:
                            raise ValueError('Page exceeds the hosted inspection size limit.')
                    soup = BeautifulSoup(bytes(body), 'html.parser')
                    for tag in soup(['script', 'style', 'noscript']):
                        tag.decompose()
                    full = {
                        'final_url': url, 'status_code': response.status_code,
                        'redirect_chain': chain, 'page_text': soup.get_text(' ', strip=True)[:5000],
                        'page_title': soup.title.get_text() if soup.title else None,
                        'forms': [{'action':urljoin(url, f.get('action') or url), 'has_password_field':bool(f.select_one('input[type=password]'))} for f in soup.select('form')[:20]],
                        'links': [{'href':urljoin(url,a['href']), 'text':a.get_text()[:80]} for a in soup.select('a[href]')[:30]],
                        'screenshot_base64':None, 'network_requests':[],
                        'response_headers':dict(response.headers),
                        'inspection_mode':'http-only',
                        'limitations':'JavaScript was not executed; no screenshot, rendered DOM or browser network activity was captured.',
                    }
                    return full, full
            raise ValueError('Too many redirects.')
    except Exception as exc:
        error = {'error': str(exc), 'inspection_mode':'http-only', 'incomplete': True}
        return error, error
