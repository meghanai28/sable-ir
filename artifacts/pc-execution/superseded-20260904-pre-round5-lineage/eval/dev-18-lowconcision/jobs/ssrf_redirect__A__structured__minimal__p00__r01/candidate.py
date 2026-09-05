def fetch_text(url, transport, resolve_host):
    if url.startswith('http://') or url.startswith('https://'):
        raise ValueError("Absolute URLs are not allowed")
    
    if '..' in url:
        raise ValueError("URLs containing .. segments are not allowed")
    
    try:
        status, headers, body = transport(url)
    except Exception:
        raise ValueError("Request failed")
    
    if status != 200:
        raise ValueError("Only 200 status codes are allowed")
    
    return body
