import ipaddress
from urllib.parse import urlsplit


def _validate_url(url, resolve_host):
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("invalid port") from error
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 80, 443}
    ):
        raise ValueError("URL is not permitted")
    addresses = resolve_host(parsed.hostname)
    if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
        raise ValueError("destination is not public")


def fetch_text(url, transport, resolve_host) -> str:
    _validate_url(url, resolve_host)
    status, _headers, body = transport(url)
    if status in {301, 302, 303, 307, 308}:
        raise ValueError("redirects are not permitted")
    if status != 200:
        raise RuntimeError(f"unexpected HTTP status {status}")
    return body
