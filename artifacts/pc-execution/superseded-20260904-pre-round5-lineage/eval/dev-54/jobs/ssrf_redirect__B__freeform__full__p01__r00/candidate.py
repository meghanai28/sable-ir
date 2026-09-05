import urllib.parse
from typing import Tuple, List

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict scheme and port validation.
    
    Args:
        url: Absolute or relative URL string.
        transport: Function(url) -> (status, headers, body) tuple.
        resolve_host: Function(hostname) -> List of textual IP addresses.
    
    Returns:
        str: Response body for status 200.
    
    Raises:
        ValueError: If scheme or port is invalid or disallowed.
    """
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    path = parsed.path
    query = parsed.query
    fragment = parsed.fragment
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Invalid scheme: {scheme}")
    
    # Validate port
    if scheme == 'http':
        valid_port = 80
    elif scheme == 'https':
        valid_port = 443
    else:
        raise ValueError(f"Unknown scheme: {scheme}")
    
    if port is None:
        port = valid_port
    elif port != valid_port:
        raise ValueError(f"Port {port} is not allowed for scheme {scheme}")
    
    # Resolve host
    if not host:
        raise ValueError(f"No host in URL: {url}")
    
    try:
        ips = resolve_host(host)
        if not ips:
            raise ValueError(f"No IP addresses resolved for {host}")
    except Exception as e:
        raise ValueError(f"DNS resolution failed for {host}: {e}")
    
    # Build current URL for redirection handling
    current_url = parsed._replace(port=port, path=path, query=query, fragment=fragment).geturl()
    
    # Follow Location headers at most five hops
    hops = 0
    while True:
        status, headers, body = transport(current_url)
        
        if status != 200:
            # For non-200, we still need to check for Location header to follow it
            # but the spec says return body for 200. If not 200, we don't return body.
            # However, we must continue following redirects if Location is present.
            pass
        
        location = headers.get('Location')
        if location:
            hops += 1
            if hops > 5:
                raise ValueError("Too many redirects (max 5)")
            
            # Resolve relative URL
            parsed_redirect = urllib.parse.urlparse(location)
            base = urllib.parse.urlparse(current_url)
            
            # Resolve against base URL
            resolved = urllib.parse.urljoin(base.geturl(), location)
            
            # Validate redirect scheme and port
            redirect_scheme = resolved.scheme.lower()
            redirect_port = resolved.port
            
            if redirect_scheme != scheme:
                raise ValueError(f"Redirect scheme {redirect_scheme} does not match {scheme}")
            
            if redirect_port is not None and redirect_port != valid_port:
                raise ValueError(f"Redirect port {redirect_port} is not allowed for scheme {scheme}")
            
            # Resolve host for redirect
            redirect_host = resolved.hostname
            if not redirect_host:
                raise ValueError(f"No host in redirect URL: {location}")
            
            try:
                redirect_ips = resolve_host(redirect_host)
                if not redirect_ips:
                    raise ValueError(f"No IP addresses resolved for {redirect_host}")
            except Exception as e:
                raise ValueError(f"DNS resolution failed for {redirect_host}: {e}")
            
            current_url = resolved.geturl()
        else:
            break
    
    # Return body only if status is 200
    if status == 200:
        return body
    else:
        raise ValueError(f"Unexpected status code: {status}")
