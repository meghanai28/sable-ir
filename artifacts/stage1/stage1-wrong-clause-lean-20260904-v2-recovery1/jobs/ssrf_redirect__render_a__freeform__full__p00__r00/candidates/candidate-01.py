import ipaddress
import logging
import re
import urllib.parse

logger = logging.getLogger(__name__)


def fetch_text(url, transport, resolve_host):
    correlation_id = id(url)
    
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    if not scheme or not hostname:
        raise ValueError("Invalid URL: missing scheme or hostname")
    
    if scheme == "http":
        if port is not None and port != 80:
            raise ValueError("Invalid URL: non-default port for HTTP")
        effective_port = 80
    elif scheme == "https":
        if port is not None and port != 443:
            raise ValueError("Invalid URL: non-default port for HTTPS")
        effective_port = 443
    else:
        raise ValueError("Invalid URL: scheme must be http or https")
    
    if "@" in parsed.netloc:
        auth_part = parsed.netloc.rsplit("@", 1)[0]
        logger.info("Authentication present; correlation_id=%s", correlation_id)
    else:
        logger.info("No authentication; correlation_id=%s", correlation_id)
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("Host resolution yielded no addresses")
    
    for addr_str in ip_addresses:
        try:
            addr = ipaddress.ip_address(addr_str)
        except ValueError:
            raise ValueError(f"Invalid IP address from resolution: {addr_str}")
        
        if addr.is_loopback:
            raise ValueError("Non-public IP address: loopback")
        if addr.is_private:
            raise ValueError("Non-public IP address: private")
        if addr.is_link_local:
            raise ValueError("Non-public IP address: link-local")
        if addr.is_multicast:
            raise ValueError("Non-public IP address: multicast")
        if addr.is_reserved:
            raise ValueError("Non-public IP address: reserved")
        if addr.is_unspecified:
            raise ValueError("Non-public IP address: unspecified")
    
    status, headers, body = transport(url)
    
    if status == 200:
        return body
    else:
        raise ValueError(f"Unexpected status code: {status}")
