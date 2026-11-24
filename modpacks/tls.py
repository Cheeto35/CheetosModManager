"""mod_manager: downloads for Mod Manager and Modpacks, ported from Sheikah Mods 1.2.3 (Shadow, MIT).

- HTTPS is checked against the bundled Mozilla list (cacert.pem, from certifi), so a PC with an out-of-date
  certificate store still connects. If that list fails, the PC's own store gets one try.
- Downloads stream to disk with a size limit instead of being held in memory.
- An optional check() sees the first link, every redirect, and where the download ended up.
"""
import os
import ssl
import time
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

CAFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cacert.pem")
MIB = 1024 * 1024
MAX_FILE = 512 * MIB
CHUNK = MIB
USER_AGENT = "CheetosModManager/1.1"

_bundle = None


class DownloadError(Exception):
    pass


class CertificateError(DownloadError):
    pass


class TooLarge(DownloadError):
    pass


def context():
    """The bundled certificate list, loaded once."""
    global _bundle
    if _bundle is None:
        _bundle = ssl.create_default_context(cafile=CAFILE)
    return _bundle


def _default_contexts():
    return (context(), ssl.create_default_context())


class _CheckRedirects(HTTPRedirectHandler):
    def __init__(self, check):
        super().__init__()
        self.check = check

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if self.check:
            self.check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _cert_failure(error):
    reason = getattr(error, "reason", None) or error
    return reason if isinstance(reason, ssl.SSLCertVerificationError) else None


@contextmanager
def open_url(url, headers=None, timeout=20, check=None, contexts=None):
    if check:
        check(url)
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    https = urlparse(url).scheme == "https"
    failure = None
    response = None
    for ctx in (contexts or _default_contexts()) if https else (None,):
        handlers = [_CheckRedirects(check)] + ([HTTPSHandler(context=ctx)] if ctx else [])
        try:
            response = build_opener(*handlers).open(Request(url, headers=request_headers), timeout=timeout)
            break
        except Exception as error:
            failure = _cert_failure(error)
            if failure is None:
                raise
    if response is None:
        host = urlparse(url).hostname or url
        raise CertificateError(
            "Couldn't verify %s's HTTPS certificate. Check your PC's date and time, then try again "
            "(%s; %s; %s)." % (host, failure, ssl.OPENSSL_VERSION, time.strftime("%Y-%m-%d %H:%M:%S %z")))
    with response:
        if check:
            check(response.geturl())
        yield response


def fetch(url, limit, headers=None, timeout=20, check=None, contexts=None):
    """Returns (final url, bytes). Raises TooLarge past limit bytes."""
    with open_url(url, headers, timeout, check, contexts) as response:
        final = response.geturl()
        data = response.read(limit + 1)
    if len(data) > limit:
        raise TooLarge("%s is too big." % (os.path.basename(urlparse(url).path) or url))
    return final, data


def download(url, path, limit=MAX_FILE, headers=None, timeout=30, check=None, on_chunk=None, contexts=None,
             on_size=None):
    """Streams url to path in 1 MiB chunks and returns the final url. on_chunk(n) may raise to stop;
    on_size(total) gets the Content-Length (0 when unknown) before the first chunk.
    path is only touched once the server answers; if anything fails after that, the partial file is removed."""
    name = os.path.basename(urlparse(url).path) or url
    with open_url(url, headers, timeout, check, contexts) as response:
        final = response.geturl()
        try:
            with open(path, "wb") as out:
                if on_size:
                    on_size(int(response.headers.get("Content-Length") or 0))
                size = 0
                while True:
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > limit:
                        raise TooLarge("%s is bigger than the %g MiB download limit." % (name, limit / MIB))
                    if on_chunk:
                        on_chunk(len(chunk))
                    out.write(chunk)
        except BaseException:
            try:
                os.remove(path)
            except OSError:
                pass
            raise
    return final
