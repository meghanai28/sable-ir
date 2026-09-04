import urllib.parse

def fetch_text(url, transport, resolve_host):
    hops = 0
    current_url = url
    
    while True:
        parsed = urllib.parse.urlparse(current_url)
        
        if parsed.scheme not in ('http', 'https'):
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
            raise ValueError("HTTP must use default port 80")
        if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
            raise ValueError("HTTPS must use default port 443")
        
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        host_ips = resolve_host(parsed.hostname)
        if not host_ips:
            raise ValueError("Host resolution failed")
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 303, 307, 308):
            hops += 1
            if hops > 5:
                raise ValueError("Too many redirects")
            
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")
            
            new_url = urllib.parse.urljoin(current_url, location)
            new_parsed = urllib.parse.urlparse(new_url)
            
            if new_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect to non-HTTP/HTTPS scheme not allowed")
            
            if new_parsed.scheme == 'http' and new_parsed.port is not None and new_parsed.port != 80:
                raise ValueError("Redirect HTTP must use default port 80")
            if new_parsed.scheme == 'https' and new_parsed.port is not None and new_parsed.port != 443:
                raise ValueError("Redirect HTTPS must use default port 443")
            
            if new_parsed.username is not None or new_parsed.password is not None:
                raise ValueError("Redirect with credentials not allowed")
            
            if not new_parsed.hostname:
                raise ValueError("Redirect must have a hostname")
            
            redirect_ips = resolve_host(new_parsed.hostname)
            if not redirect_ips:
                raise ValueError("Redirect host resolution failed")
            
            current_url = new_url
            continue
        
        raise ValueError(f"Unexpected status code: {status}")
