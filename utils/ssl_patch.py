"""
Patches the requests.Session to disable SSL certificate verification.

This is required on machines with corporate/intercepting proxies that inject
certificates not trusted by the bundled CA store (certifi). Without this,
calls to Google Gemini via the REST transport fail with:
  CERTIFICATE_VERIFY_FAILED: Basic Constraints of CA cert not marked critical

Import this module before importing google.generativeai.
"""
import ssl
import warnings

import urllib3
import requests
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_patched = False


def _make_no_verify_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class _NoVerifyAdapter(HTTPAdapter):
    """HTTPAdapter that skips SSL certificate verification."""

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = _make_no_verify_ssl_context()
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["ssl_context"] = _make_no_verify_ssl_context()
        return super().proxy_manager_for(proxy, **proxy_kwargs)


_OriginalSession = requests.Session


class _PatchedSession(_OriginalSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.verify = False
        adapter = _NoVerifyAdapter()
        self.mount("https://", adapter)
        self.mount("http://", adapter)


def apply():
    """Apply the SSL patch to requests.Session (idempotent)."""
    global _patched
    if _patched:
        return
    requests.Session = _PatchedSession
    _patched = True
