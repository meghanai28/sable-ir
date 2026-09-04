import ipaddress
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    if scheme == 'http':
        if port is not None and port != 80:
            raise ValueError("Non-default port for HTTP")
    elif scheme == 'https':
        if port is not None and port != 443:
            raise ValueError("Non-default port for HTTPS")
    
    if hostname is None:
        raise ValueError("Missing hostname")
    
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
            raise ValueError("Invalid IP address from resolution")
        
        if addr.version == 4:
            if addr.is_loopback:
                raise ValueError("Non-public IP address")
            if addr.is_private:
                raise ValueError("Non-public IP address")
            if addr.is_link_local:
                raise ValueError("Non-public IP address")
            if addr.is_multicast:
                raise ValueError("Non-public IP address")
            if addr.is_reserved:
                raise ValueError("Non-public IP address")
            if addr.is_unspecified:
                raise ValueError("Non-public IP address")
        elif addr.version == 6:
            if addr.is_loopback:
                raise ValueError("Non-public IP address")
            if addr.is_private:
                raise ValueError("Non-public IP address")
            if addr.is_link_local:
                raise ValueError("Non-public IP address")
            if addr.is_multicast:
                raise ValueError("Non-public IP address")
            if addr.is_reserved:
                raise ValueError("Non-public IP address")
            if addr.is_unspecified:
                raise ValueError("Non-public IP address")
    
    status, headers, body = transport(url)
    
    if status == 200:
        if isinstance(body, bytes):
            return body.decode('utf-8')
        return str(body)
    
    if 300 <= status < 400:
        raise ValueError("Redirect not allowed")
    
    raise ValueError("Unexpected status")
