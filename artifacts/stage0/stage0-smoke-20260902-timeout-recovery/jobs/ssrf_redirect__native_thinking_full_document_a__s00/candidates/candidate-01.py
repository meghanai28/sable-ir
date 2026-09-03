import ipaddress
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("disallowed request")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("disallowed request")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("disallowed request")

    default_port = 443 if parsed.scheme == "https" else 80
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("disallowed request")

    try:
        resolved = resolve_host(hostname)
    except Exception:
        raise ValueError("disallowed request")

    if isinstance(resolved, str):
        resolved = [resolved]

    if not resolved:
        raise ValueError("disallowed request")

    for ip_str in resolved:
        try:
            addr = ipaddress.ip_address(ip_str)
        except Exception:
            raise ValueError("disallowed request")
        if not addr.is_global:
            raise ValueError("disallowed request")

    try:
        status, headers, body = transport(url)
    except Exception:
        raise ValueError("disallowed request")

    if 300 <= status < 400:
        raise ValueError("disallowed request")

    if status != 200:
        raise ValueError("disallowed request")

    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)
