import urllib.parse
import ipaddress

def fetch_text(url, transport, resolve_host):
    max_redirects = 5
    current_url = url
    hops = 0
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        scheme = parsed.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError("Disallowed URL scheme")
        
        if scheme == 'http':
            default_port = 80
        else:
            default_port = 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError("Disallowed non-default port")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        ip_texts = resolve_host(hostname)
        if not ip_texts:
            raise ValueError("Host resolution failed")
        
        for ip_text in ip_texts:
            try:
                ip = ipaddress.ip_address(ip_text)
            except ValueError:
                raise ValueError("Invalid IP address from DNS")
            
            if ip.is_loopback:
                raise ValueError("Disallowed loopback address")
            if ip.is_multicast:
                raise ValueError("Disallowed multicast address")
            if ip.is_link_local:
                raise ValueError("Disallowed link-local address")
            if ip.is_private:
                raise ValueError("Disallowed private address")
            if ip.version == 4:
                if ip.is_reserved:
                    raise ValueError("Disallowed reserved address")
            if ip.version == 6:
                if ip.is_site_local:
                    raise ValueError("Disallowed site-local address")
                if ip.ipv4_mapped is not None:
                    ipv4 = ip.ipv4_mapped
                    if ipv4.is_loopback or ipv4.is_private or ipv4.is_reserved or ipv4.is_multicast or ipv4.is_link_local:
                        raise ValueError("Disallowed IPv4-mapped address")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            if hops >= max_redirects:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if location is None:
                raise ValueError("Redirect without Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            hops += 1
            continue
        
        raise ValueError(f"Unsupported HTTP status: {status}")
