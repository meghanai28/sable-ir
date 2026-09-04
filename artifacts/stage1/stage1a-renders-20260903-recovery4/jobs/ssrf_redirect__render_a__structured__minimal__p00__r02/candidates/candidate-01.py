import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed URL: scheme must be http or https")
    
    port = parsed.port
    if scheme == 'http' and port is not None and port != 80:
        raise ValueError("Disallowed URL: http must use default port 80")
    if scheme == 'https' and port is not None and port != 443:
        raise ValueError("Disallowed URL: https must use default port 443")
    
    status, headers, body = transport(url)
    
    if 300 <= status < 400:
        raise ValueError("Redirect responses are not allowed")
    
    if status == 200:
        return body
    
    raise ValueError(f"Unexpected status code: {status}")
