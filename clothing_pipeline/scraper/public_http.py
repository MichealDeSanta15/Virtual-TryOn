"""Ordinary requests/urllib3 HTTP with public-IP-pinned socket connections.

Fixed host allowlist and redirects are checked by SafeTransport. This layer also
rejects private/mixed DNS answers, connects to the validated numeric address,
and keeps the original hostname for TLS verification. No proxy or stealth mode.
"""
import ipaddress
import socket
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from urllib3.util.connection import create_connection
from clothing_pipeline.config import USER_AGENT


class PublicConnectionMixin:
    def _new_conn(self):
        records = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not records or any(not ipaddress.ip_address(record[4][0]).is_global for record in records):
            raise OSError('Non-public destination refused')
        last_error = None
        for _, _, _, _, address in records:
            try:
                # Numeric address: no second hostname lookup / DNS rebinding window.
                return create_connection((address[0], self.port), self.timeout,
                                         self.source_address, self.socket_options)
            except OSError as exc:
                last_error = exc
        raise OSError('Could not connect to public destination') from last_error


class PublicHTTPConnection(PublicConnectionMixin, HTTPConnection):
    pass


class PublicHTTPSConnection(PublicConnectionMixin, HTTPSConnection):
    pass


class PublicHTTPPool(HTTPConnectionPool):
    ConnectionCls = PublicHTTPConnection


class PublicHTTPSPool(HTTPSConnectionPool):
    ConnectionCls = PublicHTTPSConnection


class PublicAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        super().init_poolmanager(*args, **kwargs)
        # Per-manager copy, not a mutation of urllib3's process-wide dictionary.
        self.poolmanager.pool_classes_by_scheme = {'http':PublicHTTPPool, 'https':PublicHTTPSPool}


def fetch_public(url, max_bytes):
    # Defense in depth for direct callers of this module.
    from .network import allowed_url
    if not allowed_url(url):
        raise ValueError('Unapproved remote host or URL')
    started = time.monotonic()
    with requests.Session() as session:
        session.trust_env = False  # Never route these requests via an unvalidated env proxy.
        session.headers['User-Agent'] = USER_AGENT
        session.mount('http://', PublicAdapter(max_retries=0))
        session.mount('https://', PublicAdapter(max_retries=0))
        with session.get(url, stream=True, allow_redirects=False, timeout=(10, 15)) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                return response.status_code, b'', dict(response.headers)
            size = response.headers.get('Content-Length')
            if size and int(size) > max_bytes:
                raise ValueError('Remote response too large')
            data = bytearray()
            for chunk in response.iter_content(65536):
                if time.monotonic()-started > 20:
                    raise TimeoutError('Remote response exceeded transfer deadline')
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError('Remote response too large')
            return response.status_code, bytes(data), dict(response.headers)
