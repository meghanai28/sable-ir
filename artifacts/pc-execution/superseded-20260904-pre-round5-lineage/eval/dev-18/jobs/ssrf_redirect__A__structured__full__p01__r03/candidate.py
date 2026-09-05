def fetch_text(url: str, transport, resolve_host) -> str:
    from urllib.parse import urlparse, urljoin, parse_qs
    import socket

    def is_safe_subpath(target_url: str, origin_url: str) -> bool:
        """Check if target_url is a subpath of origin_url."""
        try:
            target_parsed = urlparse(target_url)
            origin_parsed = urlparse(origin_url)
            # Scheme and netloc must match
            if target_parsed.scheme != origin_parsed.scheme or target_parsed.netloc != origin_parsed.netloc:
                return False
            # Path must be within origin path
            # If origin path is empty, target must be absolute or relative to origin
            if not origin_parsed.path:
                return False
            # Normalize paths to handle .. and .
            origin_path_parts = [p for p in origin_parsed.path.split('/') if p and p != '..']
            target_path_parts = [p for p in target_parsed.path.split('/') if p and p != '..']
            
            # Target must start with origin path
            if not (target_path_parts[:len(origin_path_parts)] == origin_path_parts):
                return False
            return True
        except Exception:
            return False

    # Parse initial URL
    initial_parsed = urlparse(url)
    
    # Check scheme and port
    if initial_parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS are allowed")
    
    # Resolve hostname
    hostname = initial_parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("resolve_host returned no IP addresses")
    
    # Determine target URL for connection
    target_url = url
    
    # Handle redirects
    while True:
        status, headers, body = transport(target_url)
        
        if status == 300:
            # Multiple Choice - follow first Location if present
            location = headers.get('Location')
            if location:
                target_url = location
                continue
            else:
                raise ValueError("Redirect without Location header")
        
        if status == 301 or status == 302 or status == 303 or status == 307 or status == 308:
            # Redirect
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect without Location header")
            
            # Resolve the new URL
            new_parsed = urlparse(location)
            target_url = new_parsed.geturl()
            
            # Check if the new URL is safe (subpath)
            if not is_safe_subpath(target_url, initial_parsed.geturl()):
                raise ValueError("Redirect to unsafe URL")
            
            continue
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return body
        return body.decode('utf-8') if isinstance(body, bytes) else body

    raise ValueError("Unexpected response")
