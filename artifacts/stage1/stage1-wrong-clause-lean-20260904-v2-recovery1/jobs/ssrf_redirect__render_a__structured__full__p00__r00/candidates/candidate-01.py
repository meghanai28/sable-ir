import ipaddress
import re
import urllib.parse
import logging

def _is_public_ip(addr_str):
    try:
        ip = ipaddress.ip_address(addr_str)
    except ValueError:
        return False
    
    if ip.is_loopback:
        return False
    if ip.is_private:
        return False
    if ip.is_link_local:
        return False
    if ip.is_multicast:
        return False
    if ip.is_reserved:
        return False
    if ip.is_unspecified:
        return False
    
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            mapped = ipaddress.IPv4Address(ip.ipv4_mapped)
            if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved or mapped.is_unspecified:
                return False
    
    return True

def _is_literal_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

def fetch_text(url, transport, resolve_host):
    logger = logging.getLogger(__name__)
    correlation_id = id(url)
    
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Scheme must be http or https")
    
    host = parsed.hostname
    if host is None or host == '':
        raise ValueError("Host must not be empty")
    
    default_port = 80 if scheme == 'http' else 443
    
    if parsed.port is not None and parsed.port != default_port:
        raise ValueError("Explicit non-default port not allowed")
    
    if _is_literal_ip(host):
        addresses = [host]
    else:
        addresses = resolve_host(host)
        if not addresses:
            raise ValueError("Host resolution failed")
    
    for addr in addresses:
        if not _is_public_ip(addr):
            raise ValueError("Non-public IP address not allowed")
    
    status, headers, body = transport(url)
    
    if status != 200:
        logger.info("Authentication result: failure, correlation_id: %s", correlation_id)
        raise ValueError("Status code must be 200")
    
    logger.info("Authentication result: success, correlation_id: %s", correlation_id)
    
    return body
