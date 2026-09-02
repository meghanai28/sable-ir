import ipaddress
from urllib.parse import urljoin, urlsplit


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
    current = url
    for hop in range(6):
        _validate_url(current, resolve_host)
        status, headers, body = transport(current)
        if status == 200:
            return body
        if status not in {301, 302, 303, 307, 308}:
            raise RuntimeError(f"unexpected HTTP status {status}")
        if hop == 5:
            raise ValueError("too many redirects")
        location = next(
            (value for key, value in headers.items() if key.casefold() == "location"), None
        )
        if not location:
            raise ValueError("redirect is missing Location")
        current = urljoin(current, location)
    raise ValueError("too many redirects")
