import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response as a string for status 200.
    
    Raises:
        ValueError: If the scheme/port is invalid, hostname cannot be resolved,
                    or unsafe redirects are detected.
    """
    parsed_url = urllib.parse.urlparse(url)
    
    # Check scheme and port
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # Default ports
    default_ports = {'http': 80, 'https': 443}
    
    if scheme not in default_ports:
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Check port
    if port is None:
        expected_port = default_ports[scheme]
    else:
        expected_port = port
    
    if port != expected_port:
        raise ValueError(f"Port {port} is not the default for scheme {scheme}")
    
    current_url = url
    redirect_count = 0
    
    while True:
        # Resolve hostname
        hostname = parsed_url.hostname
        if hostname is None:
            raise ValueError("Invalid URL: missing hostname")
        
        try:
            ips = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
        
        if not ips:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
        
        # Create a new URL object with the resolved IP (first one)
        resolved_url = parsed_url._replace(netloc=ips[0])
        current_url = resolved_url.geturl()
        
        # Check for .. segments in the netloc or path
        netloc_parts = current_url.split('://')[1].split('/')[0].split(':')
        if '..' in netloc_parts:
            raise ValueError("Unsafe .. segment in netloc")
        
        # Get headers and body
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Handle redirects
        if 'location' in headers:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            location = headers['location']
            # Resolve redirect URL
            try:
                redirect_parsed = urllib.parse.urlparse(location)
            except Exception:
                raise ValueError(f"Invalid redirect URL: {location}")
            
            # Check scheme and port match initial request
            if redirect_parsed.scheme.lower() != scheme or redirect_parsed.port != expected_port:
                raise ValueError(f"Redirect to disallowed scheme/port: {redirect_parsed.scheme}:{redirect_parsed.port}")
            
            # Check for .. segments in the redirect URL
            path_parts = redirect_parsed.path.split('/')
            if '..' in path_parts:
                raise ValueError("Unsafe .. segment in redirect path")
            
            # Resolve against current URL
            resolved_redirect = urllib.parse.urljoin(current_url, location)
            current_url = resolved_redirect
            
            # Re-parse for next iteration
            parsed_url = urllib.parse.urlparse(current_url)
        else:
            break
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
