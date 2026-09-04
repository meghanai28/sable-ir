import urllib.parse
import ipaddress

def _is_public_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private:
            return False
        if ip.is_loopback:
            return False
        if ip.is_reserved:
            return False
        if ip.is_multicast:
            return False
        if ip.is_link_local:
            return False
        if ip.version == 4:
            if ip.is_unspecified:
                return False
        else:
            if ip.is_unspecified:
                return False
        if ip.is_site_local:
            return False
        return True
    except ValueError:
        return False

def _validate_url(url, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Invalid scheme")
    
    default_port = 443 if parsed.scheme == 'https' else 80
    
    netloc = parsed.netloc
    if '@' in netloc:
        raise ValueError("Credentials not allowed")
    
    if ':' in netloc:
        host_part, port_part = netloc.rsplit(':', 1)
        if port_part.isdigit():
            port = int(port_part)
            if host_part.startswith('[') and host_part.endswith(']'):
                hostname = host_part[1:-1]
            else:
                hostname = host_part
            if port != default_port:
                raise ValueError("Non-default port not allowed")
        else:
            hostname = netloc
    else:
        hostname = netloc
    
    if not hostname:
        raise ValueError("Empty hostname")
    
    try:
        ip_addrs = resolve_host(hostname)
    except Exception:
        raise ValueError("DNS resolution failed")
    
    if not ip_addrs:
        raise ValueError("DNS resolution failed")
    
    for ip_str in ip_addrs:
        if not _is_public_ip(ip_str):
            raise ValueError("Non-public IP address")
    
    return parsed

def _resolve_redirect(base_url, location):
    return urllib.parse.urljoin(base_url, location)

def fetch_text(url, transport, resolve_host):
    redirect_count = 0
    current_url = url
    
    while True:
        parsed = _validate_url(current_url, resolve_host)
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            location = None
            for key, value in headers:
                if key.lower() == 'location':
                    location = value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = _resolve_redirect(current_url, location)
            continue
        
        raise ValueError(f"Non-200 status: {status}")
