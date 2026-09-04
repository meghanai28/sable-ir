import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are allowed")
    
    port = parsed.port
    if scheme == 'http' and port is not None and port != 80:
        raise ValueError("Non-default port not allowed")
    if scheme == 'https' and port is not None and port != 443:
        raise ValueError("Non-default port not allowed")
    if port is None:
        pass
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not allowed")
    
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status code: {status}")
