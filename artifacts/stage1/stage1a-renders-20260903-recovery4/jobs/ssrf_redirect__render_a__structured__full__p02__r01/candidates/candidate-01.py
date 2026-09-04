import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Missing hostname")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        else:
            port = 443
    
    if scheme == 'http' and port != 80:
        raise ValueError("Non-default port for HTTP")
    if scheme == 'https' and port != 443:
        raise ValueError("Non-default port for HTTPS")
    
    try:
        addr = ipaddress.ip_address(hostname)
        ip_texts = [str(addr)]
    except ValueError:
        ip_texts = resolve_host(hostname)
        if not ip_texts:
            raise ValueError("Host resolution failed")
    
    for ip_text in ip_texts:
        try:
            addr = ipaddress.ip_address(ip_text)
        except ValueError:
            raise ValueError("Invalid IP address")
        
        if addr.is_loopback:
            raise ValueError("Loopback address not allowed")
        if addr.is_private:
            raise ValueError("Private address not allowed")
        if addr.is_link_local:
            raise ValueError("Link-local address not allowed")
        if addr.is_multicast:
            raise ValueError("Multicast address not allowed")
        if addr.is_reserved:
            raise ValueError("Reserved address not allowed")
        if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
            mapped = ipaddress.IPv4Address(int(addr.ipv4_mapped))
            if mapped.is_loopback or mapped.is_private or mapped.is_link_local or mapped.is_multicast or mapped.is_reserved:
                raise ValueError("Non-public mapped IPv4 address")
    
    status, headers, body = transport(url)
    
    if status == 200:
        if isinstance(body, bytes):
            return body.decode('utf-8')
        return str(body)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    raise ValueError("Unexpected status")
