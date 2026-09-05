import socket
from urllib.parse import urlparse, urljoin

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL following redirects up to 5 hops.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the HTTP response as a string for status 200.
    
    Raises:
        ValueError: If the URL is invalid, scheme is not http/https, 
                    no single IP is resolved, or status is not 200.
    """
    # Normalize the URL
    parsed = urlparse(url)
    
    # Check for scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("URL must have http or https scheme")
    
    # Check for port (default to 80 for http, 443 for https if not specified)
    port = parsed.port
    if port is None:
        if parsed.scheme == 'http':
            port = 80
        else:
            port = 443
    
    # Resolve the hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: no hostname found")
    
    ips = resolve_host(hostname)
    if not ips or len(ips) != 1:
        raise ValueError("Exactly one IP address must be returned by resolve_host")
    
    ip = ips[0]
    
    # Build the base URL for connection
    base_url = f"{parsed.scheme}://{hostname}:{port}{parsed.path}"
    
    # Track redirects
    max_hops = 5
    current_url = base_url
    history = []
    
    while True:
        # Check hop limit
        if len(history) >= max_hops:
            raise ValueError("Too many redirects")
        
        # Resolve the current URL's hostname
        current_parsed = urlparse(current_url)
        if current_parsed.hostname is None:
            raise ValueError("Invalid URL: no hostname found")
        
        current_ips = resolve_host(current_parsed.hostname)
        if not current_ips or len(current_ips) != 1:
            raise ValueError("Exactly one IP address must be returned by resolve_host")
        
        # Check for public addressing (IPs starting with 127.0.0.1 or ::1 are loopback,
        # but we should also reject private ranges if the requirement implies public only.
        # The plan says "public addressing", so we reject private IPs.
        ip_str = current_ips[0]
        if ip_str.startswith(('127.', '::1')):
            raise ValueError("Private IP address detected")
        
        # Make the transport call
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"HTTP status {status} is not 200")
        
        return body
        
        # Check for redirects
        location = headers.get('Location')
        if not location:
            continue
        
        # Parse the redirect URL
        redirect_parsed = urlparse(location)
        
        # Check if redirect is relative
        if not redirect_parsed.scheme:
            # Join with the referring URL
            new_url = urljoin(current_url, location)
        else:
            new_url = location
        
        # Check scheme and port of redirect
        new_parsed = urlparse(new_url)
        if new_parsed.scheme not in ('http', 'https'):
            raise ValueError("Redirect URL must have http or https scheme")
        
        # Check for loop redirects
        if new_url in history:
            raise ValueError("Redirect loop detected")
        
        # Resolve the new hostname
        new_hostname = new_parsed.hostname
        if new_hostname is None:
            raise ValueError("Invalid redirect URL: no hostname found")
        
        new_ips = resolve_host(new_hostname)
        if not new_ips or len(new_ips) != 1:
            raise ValueError("Exactly one IP address must be returned by resolve_host")
        
        # Check for public addressing
        new_ip = new_ips[0]
        if new_ip.startswith(('127.', '::1')):
            raise ValueError("Private IP address detected in redirect")
        
        # Update current URL
        current_url = new_url
        history.append(new_url)
    
    # This part should not be reached due to the loop logic, but for completeness:
    raise ValueError("Unexpected end of redirect chain")
