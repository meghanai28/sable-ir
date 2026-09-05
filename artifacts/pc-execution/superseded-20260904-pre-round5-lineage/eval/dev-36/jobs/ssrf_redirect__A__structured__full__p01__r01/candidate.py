import urllib.parse
import urllib.request
import urllib.error
import socket
import ssl
from typing import Tuple, List, Optional

def resolve_host(hostname: str) -> List[str]:
    """Resolve a hostname to a list of IP addresses."""
    try:
        return socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security controls.
    
    Args:
        url: The URL to fetch from.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns IP addresses.
    
    Returns:
        The body text of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong scheme, port, redirect, etc.).
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    initial_scheme = parsed_url.scheme.lower()
    initial_port = parsed_url.port or (443 if initial_scheme == 'https' else 80)
    initial_host = parsed_url.hostname
    
    # Validate scheme and port
    allowed_schemes = ['http', 'https']
    if initial_scheme not in allowed_schemes:
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed. Got: {initial_scheme}")
    
    if initial_port not in [80, 443]:
        raise ValueError(f"Only default ports (80, 443) are allowed. Got: {initial_port}")
    
    # Resolve the initial hostname
    try:
        resolved_ips = resolve_host(initial_host)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # Store the initial destination for redirect checks
    initial_destination = (initial_scheme, initial_host, initial_port)
    
    # Prepare the request
    request = urllib.request.Request(url)
    
    # Open the connection and handle the response
    try:
        response = urllib.request.urlopen(request)
        
        # Check if it's a redirect
        if response.status == 301 or response.status == 302 or response.status == 303 or response.status == 307:
            # Extract the redirect location
            location = response.headers.get('Location')
            if not location:
                raise ValueError("Redirect response without Location header")
            
            # Parse the redirect URL
            redirect_url = urllib.parse.urlparse(location)
            
            # Check if the redirect is to the same scheme and default port
            redirect_scheme = redirect_url.scheme.lower()
            redirect_port = redirect_url.port or (443 if redirect_scheme == 'https' else 80)
            redirect_host = redirect_url.hostname
            
            if redirect_scheme != initial_scheme or redirect_port != initial_port:
                raise ValueError("Redirect to a different scheme or non-default port is not allowed")
            
            # Do not follow the redirect; raise ValueError
            raise ValueError("Redirects are not allowed")
        
        # Check status code
        if response.status != 200:
            raise ValueError(f"Expected status 200, got {response.status}")
        
        # Read the body
        body = response.read().decode('utf-8')
        
        return body
    
    except urllib.error.HTTPError as e:
        if e.code == 301 or e.code == 302 or e.code == 303 or e.code == 307:
            raise ValueError("Redirects are not allowed")
        raise ValueError(f"HTTP error: {e.code}")
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
