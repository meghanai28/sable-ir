import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    original_url = url
    redirect_count = 0
    max_redirects = 5
    
    while True:
        parsed = urllib.parse.urlparse(url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Invalid scheme")
        
        default_port = 80 if scheme == 'http' else 443
        port = parsed.port
        if port is not None and port != default_port:
            raise ValueError("Non-default port")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Userinfo not allowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("No IP addresses resolved")
        
        for ip_str in ip_addresses:
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local or getattr(ip, 'is_site_local', False):
                    raise ValueError("Non-public IP address")
            except ValueError:
                raise ValueError("Invalid IP address")
        
        netloc = hostname
        path = parsed.path if parsed.path else '/'
        query = '?' + parsed.query if parsed.query else ''
        fragment = ''
        reconstructed = urllib.parse.urlunparse((scheme, netloc, path, '', parsed.query, fragment))
        
        status, headers, body = transport(reconstructed)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location = None
            for header_name, header_value in headers:
                if header_name.lower() == 'location':
                    location = header_value
                    break
            
            if location is None:
                raise ValueError("Redirect without Location header")
            
            url = urllib.parse.urljoin(url, location)
            continue
        
        raise ValueError(f"Non-200 final status: {status}")
