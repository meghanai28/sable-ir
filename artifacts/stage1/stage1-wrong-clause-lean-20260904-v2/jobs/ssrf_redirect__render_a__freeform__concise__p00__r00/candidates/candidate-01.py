import ipaddress
import re
import secrets
import urllib.parse
import logging

logger = logging.getLogger(__name__)

def _is_publicly_routable(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )

def _strip_url_credentials(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.username is not None or parsed.password is not None:
        netloc = parsed.hostname or ""
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        parsed = parsed._replace(netloc=netloc)
    return urllib.parse.urlunparse(parsed)

def _strip_sensitive_headers(headers):
    if headers is None:
        return None
    sensitive_names = {
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-csrf-token",
        "api-key",
        "bearer",
        "token",
    }
    result = {}
    for name, value in headers.items():
        lower_name = name.lower()
        if lower_name in sensitive_names:
            result[name] = "[REDACTED]"
        else:
            result[name] = value
    return result

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError("Disallowed scheme")
    
    port = parsed.port
    if port is None:
        if scheme == "http":
            port = 80
        else:
            port = 443
    
    if scheme == "http" and port != 80:
        raise ValueError("Disallowed port for HTTP")
    if scheme == "https" and port != 443:
        raise ValueError("Disallowed port for HTTPS")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    resolved_ips = resolve_host(hostname)
    for ip_str in resolved_ips:
        if not _is_publicly_routable(ip_str):
            raise ValueError("Non-publicly routable IP address")
    
    correlation_id = secrets.token_hex(16)
    
    stripped_url = _strip_url_credentials(url)
    
    try:
        status, headers, body = transport(url)
    except Exception as e:
        auth_result = "failure"
        safe_headers = None
        logger.info(
            "transport invocation: correlation_id=%s auth_result=%s url=%s headers=%s error=%s",
            correlation_id,
            auth_result,
            stripped_url,
            safe_headers,
            str(e),
        )
        raise
    
    auth_result = "success" if status == 200 else "failure"
    safe_headers = _strip_sensitive_headers(headers)
    
    logger.info(
        "transport invocation: correlation_id=%s auth_result=%s url=%s status=%s headers=%s",
        correlation_id,
        auth_result,
        stripped_url,
        status,
        safe_headers,
    )
    
    if status != 200:
        raise ValueError(f"Unexpected status: {status}")
    
    return body
