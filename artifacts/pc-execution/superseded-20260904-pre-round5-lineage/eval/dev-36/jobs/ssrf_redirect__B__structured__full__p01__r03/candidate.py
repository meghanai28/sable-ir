import urllib.request
import urllib.parse
import urllib.error
import socket
import re
from typing import Tuple, List, Optional, Text

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
    
    # Resolve hostname before opening connection
    try:
        resolved_ips = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Check for directory traversal in the initial URL
    if '..' in parsed_url.path or parsed_url.path.startswith('..'):
        raise ValueError("URL contains directory traversal sequences")
    
    # Track Location hops (max 5)
    location_hops = 0
    current_url = url
    
    while True:
        # Check if we've exceeded max hops
        if location_hops > 5:
            raise ValueError("Maximum number of Location hops exceeded")
        
        # Get the response
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
        
        # Check status code
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Process Location headers
        location_header = headers.get('Location')
        if location_header:
            location_hops += 1
            location_url = location_header
            
            # Resolve the new hostname
            try:
                new_parsed = urllib.parse.urlparse(location_url)
                new_hostname = new_parsed.hostname
                new_port = new_parsed.port
                new_credentials = new_parsed.username or new_parsed.password
                
                # Check if hostname changed
                if new_hostname != hostname:
                    resolved_new_ips = resolve_host(new_hostname)
                else:
                    resolved_new_ips = resolved_ips
                
                # Check if port changed
                if new_port != port:
                    raise ValueError("Port must remain the same")
                
                # Check if credentials changed
                if new_credentials != credentials:
                    raise ValueError("Credentials must remain the same")
                
                # Check DNS resolution
                if resolved_new_ips != resolved_ips:
                    raise ValueError("DNS resolution must remain the same")
                
                # Check public address (IP)
                if resolved_new_ips[0] != resolved_ips[0]:
                    raise ValueError("Public IP address must remain the same")
                
                # Build the new current URL
                # Handle relative URLs
                if not new_parsed.scheme:
                    # It's a relative URL, resolve against current URL
                    current_url = urllib.parse.urljoin(current_url, location_url)
                else:
                    current_url = location_url
            
            except ValueError as e:
                raise ValueError(f"Invalid Location header: {str(e)}")
        
        # Check if we've exceeded max hops (including the current one)
        if location_hops > 5:
            raise ValueError("Maximum number of Location hops exceeded")
        
        # Return the body
        return body.decode('utf-8') if isinstance(body, bytes) else body

def main():
    """Main function to test the implementation."""
    # This is just for demonstration purposes
    pass

if __name__ == "__main__":
    main()
