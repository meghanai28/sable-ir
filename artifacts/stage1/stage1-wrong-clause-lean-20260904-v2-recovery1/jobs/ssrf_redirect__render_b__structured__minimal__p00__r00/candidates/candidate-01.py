import ipaddress
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)


def _is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or getattr(ip, "is_site_local", False)
        )
    except ValueError:
        return False


def _validate_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid URL")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid scheme")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials not allowed")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")

    port = parsed.port
    if parsed.scheme == "http" and port != 80:
        if port is None:
            port = 80
        else:
            raise ValueError("Invalid port for HTTP")
    elif parsed.scheme == "https" and port != 443:
        if port is None:
            port = 443
        else:
            raise ValueError("Invalid port for HTTPS")

    if not hostname:
        raise ValueError("Empty hostname")

    return parsed, hostname, port


def fetch_text(url, transport, resolve_host):
    parsed, hostname, port = _validate_url(url)

    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("DNS resolution failed")

    for ip_str in resolved_ips:
        if not _is_public_ip(ip_str):
            raise ValueError("Non-public IP address")

    netloc = hostname
    if (parsed.scheme == "http" and port != 80) or (
        parsed.scheme == "https" and port != 443
    ):
        netloc = f"{hostname}:{port}"

    safe_url = urllib.parse.urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )

    correlation_id = id(url)

    logger.info(
        "Request authorized: scheme=%s, host=%s, correlation=%s",
        parsed.scheme,
        hostname,
        correlation_id,
    )

    try:
        status, headers, body = transport(safe_url)
    except Exception:
        logger.warning(
            "Transport failure: correlation=%s",
            correlation_id,
        )
        raise ValueError("Transport failure")

    if status != 200:
        logger.info(
            "Request completed with non-200 status: status=%s, correlation=%s",
            status,
            correlation_id,
        )
        raise ValueError(f"Unexpected status: {status}")

    logger.info(
        "Request succeeded: status=200, correlation=%s",
        correlation_id,
    )

    if isinstance(body, bytes):
        return body.decode("utf-8")
    return str(body)
