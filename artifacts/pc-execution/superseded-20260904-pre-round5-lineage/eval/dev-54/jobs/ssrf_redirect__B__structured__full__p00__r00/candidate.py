import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    def get_public_address():
        try:
            info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
            if info:
                return info[0][4][0]
        except socket.gaierror:
            raise ValueError("Host resolution failed")
    
    current_url = url
    max_redirects = 5
    redirects = 0
    
    while True:
        if redirects > max_redirects:
            raise ValueError("Too many redirects")
        
        try:
            req = urllib.request.Request(current_url)
            resp = transport(current_url)
        except urllib.error.HTTPError as e:
            status = e.code
            if status != 200:
                raise ValueError(f"Status {status} is not 200")
            body = e.read().decode('utf-8')
            return body
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status, headers, body = resp
        
        if status != 200:
            raise ValueError(f"Status {status} is not 200")
        
        location = headers.get('Location')
        if location:
            redirects += 1
            try:
                redirect_url = urllib.parse.urlparse(location)
                if not redirect_url.scheme:
                    redirect_url = urllib.parse.urljoin(current_url, location)
                    redirect_url = urllib.parse.urlparse(redirect_url)
                
                if redirect_url.scheme != scheme:
                    raise ValueError("Redirect scheme mismatch")
                if port != redirect_url.port:
                    raise ValueError("Redirect port mismatch")
                
                try:
                    resolved_host = resolve_host(redirect_url.hostname)
                except ValueError:
                    raise ValueError("Redirect host resolution failed")
                
                current_public = get_public_address()
                redirect_public = None
                if resolved_host:
                    for ip in resolved_host:
                        try:
                            socket.getaddrinfo(ip, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                            redirect_public = ip
                            break
                        except socket.gaierror:
                            continue
                
                if not redirect_public or redirect_public != current_public:
                    raise ValueError("Redirect public address mismatch")
                
                current_url = redirect_url.geturl()
            except ValueError:
                raise ValueError("Redirect validation failed")
        else:
            break
    
    return body
