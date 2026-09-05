import urllib.request
import urllib.parse
import urllib.error
import socket
import re
from typing import Tuple, List, Optional, Any

def resolve_host(hostname: str) -> List[str]:
    """Resolve hostname to a list of IP addresses."""
    try:
        return socket.getaddrinfo(hostname, None)[0][4][0]
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

def validate_path(url: str, base_path: str) -> bool:
    """Check if the URL is within the base path to prevent directory traversal."""
    try:
        parsed_url = urllib.parse.urlparse(url)
        base_parsed = urllib.parse.urlparse(base_path)
        
        # Normalize both paths
        normalized_url = parsed_url.path.lstrip('/')
        normalized_base = base_parsed.path.lstrip('/')
        
        # Ensure the URL path starts with the base path
        if not normalized_url.startswith(normalized_base):
            return False
        
        # Additional check for .. segments
        if '..' in normalized_url or '..' in normalized_base:
            return False
            
        return True
    except Exception:
        return False

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with security checks.
    
    Args:
        url: The URL to fetch from
        transport: Function that returns (status, headers, body)
        resolve_host: Function that resolves hostname to IP addresses
    
    Returns:
        The response body as a string for status 200
    
    Raises:
        ValueError: If the request is disallowed or resolution fails
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    hostname = parsed_url.hostname
    port = parsed_url.port
    credentials = parsed_url.username or parsed_url.password
    
    # Validate scheme and port
    allowed_schemes = ['http', 'https']
    if scheme not in allowed_schemes:
        raise ValueError(f"Only {', '.join(allowed_schemes)} schemes are allowed")
    
    if port:
        allowed_ports = {80 if scheme == 'http' else 443}
        if port not in allowed_ports:
            raise ValueError(f"Only default ports {', '.join(map(str, allowed_ports))} are allowed")
    
    # Resolve hostname before making request
    try:
        resolved_ips = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Check for directory traversal in the initial URL
    if '..' in parsed_url.path or '..' in parsed_url.netloc:
        raise ValueError("URL contains directory traversal segments")
    
    # Make the request
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
    
    # Check status code
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}")
    
    # Handle Location headers - follow at most 5 hops
    location_count = 0
    current_url = url
    
    while location_count < 5:
        location_header = headers.get('Location')
        if not location_header:
            break
        
        location_count += 1
        current_url = location_header
        
        # Parse the new URL
        new_parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme and port for the new URL
        if new_parsed.scheme.lower() not in allowed_schemes:
            raise ValueError(f"Invalid scheme in Location header: {new_parsed.scheme}")
        
        new_port = new_parsed.port
        if new_port:
            if new_port not in allowed_ports:
                raise ValueError(f"Invalid port in Location header: {new_port}")
        
        # Resolve hostname for the new URL
        new_hostname = new_parsed.hostname
        if not new_hostname:
            raise ValueError(f"No hostname in Location header: {current_url}")
        
        try:
            new_resolved_ips = resolve_host(new_hostname)
        except ValueError:
            raise ValueError(f"Failed to resolve hostname in Location header: {new_hostname}")
        
        # Check DNS resolution matches
        if set(new_resolved_ips) != set(resolved_ips):
            raise ValueError("DNS resolution mismatch in Location header")
        
        # Check public address matches
        if new_parsed.netloc != parsed_url.netloc:
            raise ValueError("Network location mismatch in Location header")
        
        # Check credentials match
        new_credentials = new_parsed.username or new_parsed.password
        if new_credentials != credentials:
            raise ValueError("Credentials mismatch in Location header")
        
        # Check scheme matches
        if new_parsed.scheme.lower() != scheme:
            raise ValueError("Scheme mismatch in Location header")
        
        # Check port matches
        if new_port != port:
            raise ValueError("Port mismatch in Location header")
        
        # Check path is beneath the base path
        if not validate_path(current_url, url):
            raise ValueError("Location URL is not beneath the base path")
        
        # Update current URL and parsed URL for next iteration
        parsed_url = new_parsed
        url = current_url
        resolved_ips = new_resolved_ips
    
    # Return the response body
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
