import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    redirect_count = 0
    
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 80 if scheme == 'http' else 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Non-default port not allowed")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                    raise ValueError("Non-public IP address")
            except ValueError:
                raise ValueError("Invalid IP address")
        
        netloc = hostname
        reconstructed = urllib.parse.urlunparse((
            scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        status, headers, body = transport(reconstructed)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
