import ipaddress
import urllib.parse


def _validate_url(url, resolve_host):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL scheme must be http or https")
    if not parsed.hostname:
        raise ValueError("URL must contain a hostname")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URL must not contain credentials")
    default_port = 443 if parsed.scheme == "https" else 80
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("URL contains an invalid port")
    if port is not None and port != default_port:
        raise ValueError("URL must use the default port for its scheme")
    try:
        ips = resolve_host(parsed.hostname)
    except Exception as exc:
        raise ValueError("DNS resolution failed") from exc
    if not ips:
        raise ValueError("DNS resolution returned no addresses")
    for ip_str in ips:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError as exc:
            raise ValueError("DNS resolution returned an invalid address") from exc
        if not addr.is_global:
            raise ValueError("DNS resolution returned a non-public address")


def _get_location(headers):
    if isinstance(headers, dict):
        for key in headers:
            if key.lower() == "location":
                return headers[key]
        return None
    try:
        for k, v in headers:
            if k.lower() == "location":
                return v
    except Exception:
        pass
    return None


def fetch_text(url, transport, resolve_host):
    current_url = url
    _validate_url(current_url, resolve_host)
    for hop in range(6):
        status, headers, body = transport(current_url)
        if status == 200:
            if isinstance(body, bytes):
                return body.decode("utf-8")
            return str(body)
        if 300 <= status < 400:
            if hop >= 5:
                raise ValueError("Too many redirects")
            location = _get_location(headers)
            if location is None:
                raise ValueError("Redirect response missing Location header")
            next_url = urllib.parse.urljoin(current_url, location)
            _validate_url(next_url, resolve_host)
            current_url = next_url
            continue
        raise ValueError(f"Unexpected HTTP status: {status}")
    raise ValueError("Too many redirects")
