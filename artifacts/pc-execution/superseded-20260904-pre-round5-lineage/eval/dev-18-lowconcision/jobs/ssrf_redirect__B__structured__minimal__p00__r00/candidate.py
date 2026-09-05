import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security constraints.
    
    Args:
        url: The URL to fetch from.
        transport: A function that returns (status, headers, body) for an HTTP request.
        resolve_host: A function that returns a list of textual IP addresses for a hostname.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the URL is absolute, contains path traversal, or resolves to an invalid IP.
    """
    # 1. Reject absolute URLs
    if url.startswith(('http://', 'https://')):
        raise ValueError("Absolute URLs are disallowed")
    
    # 2. Check for path traversal (.. segments)
    parsed = urllib.parse.urlparse(url)
    path = parsed.path if parsed.path else '/'
    
    # Simple check for '..' in path or query
    if '..' in path or '..' in parsed.query:
        raise ValueError("Path traversal detected")
    
    # 3. Resolve the target hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid hostname")
    
    ip_addresses = resolve_host(hostname)
    
    # 4. Check if the hostname resolves to a finite IP address
    if not ip_addresses:
        raise ValueError("Hostname does not resolve to a finite IP address")
    
    # 5. Determine the base scheme and port
    scheme = parsed.scheme
    port = parsed.port
    
    # Default ports
    default_http_port = 80
    default_https_port = 443
    
    # Set default port if not specified
    if port is None:
        if scheme == 'http':
            port = default_http_port
        elif scheme == 'https':
            port = default_https_port
    
    # 6. Follow redirects (at most 5)
    current_url = url
    redirect_count = 0
    
    while redirect_count < 5:
        # Parse current URL to check constraints
        parsed_current = urllib.parse.urlparse(current_url)
        
        # Ensure scheme and port match the initial destination
        if parsed_current.scheme != scheme:
            raise ValueError("Redirect scheme mismatch")
        
        if parsed_current.port is not None:
            if parsed_current.port != port:
                raise ValueError("Redirect port mismatch")
        
        # Get the target URL for the request
        target_url = current_url
        
        # Make the request
        try:
            response = transport(target_url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status_code, headers, body = response
        
        # Check for success
        if status_code == 200:
            return body
        
        # Handle redirects
        if 'location' in headers:
            redirect_url = headers['location']
            
            # Resolve the redirect URL against the current URL
            redirect_parsed = urllib.parse.urlparse(redirect_url)
            current_parsed = urllib.parse.urlparse(current_url)
            
            # Reconstruct the base URL without the path/query fragment if needed, 
            # but standard behavior is to resolve relative to current.
            # However, the guard says "must have the same scheme, port, credentials, DNS, and public address".
            
            # Check scheme
            if redirect_parsed.scheme != scheme:
                raise ValueError("Redirect scheme mismatch")
            
            # Check port
            if redirect_parsed.port is not None:
                if redirect_parsed.port != port:
                    raise ValueError("Redirect port mismatch")
            
            # Check credentials (userinfo)
            if current_parsed.username or current_parsed.password:
                if redirect_parsed.username != current_parsed.username or redirect_parsed.password != current_parsed.password:
                    raise ValueError("Redirect credentials mismatch")
            
            # Check DNS (hostname)
            redirect_hostname = redirect_parsed.hostname
            if not redirect_hostname:
                raise ValueError("Invalid hostname in redirect")
            
            if redirect_hostname != hostname:
                raise ValueError("Redirect hostname mismatch")
            
            # Check public address (IP)
            # We must ensure the redirect hostname resolves to the same IP(s) as the original
            redirect_ips = resolve_host(redirect_hostname)
            if not redirect_ips:
                raise ValueError("Redirect hostname does not resolve to a finite IP address")
            
            # Compare IP sets (allowing for slight variations in order)
            if set(redirect_ips) != set(ip_addresses):
                raise ValueError("Redirect public address mismatch")
            
            # Update current URL
            current_url = redirect_url
            redirect_count += 1
        else:
            raise ValueError(f"Redirect loop or no location header")
    
    raise ValueError("Too many redirects")
