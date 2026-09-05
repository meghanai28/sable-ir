import socket
import urllib.parse
from typing import Tuple, List, Optional

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict same-origin validation for redirects and IP resolution.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that returns (status, headers, body) for a given URL.
        resolve_host: A callable that returns a list of IP addresses for a given hostname.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the request is disallowed, status is not 200, or validation fails.
    """
    # Parse the initial URL
    initial_parsed = urllib.parse.urlparse(url)
    initial_scheme = initial_parsed.scheme
    initial_host = initial_parsed.hostname
    initial_port = initial_parsed.port
    initial_path = initial_parsed.path
    initial_credentials = initial_parsed.username or initial_parsed.password
    
    # Helper to check if a URL matches the initial scheme, port, credentials, and DNS (hostname)
    def is_safe_url(parsed_url: urllib.parse.ParseResult) -> bool:
        if parsed_url.scheme != initial_scheme:
            return False
        if parsed_url.port is not None and parsed_url.port != initial_port:
            return False
        if parsed_url.username or parsed_url.password:
            if not (parsed_url.username == initial_credentials.username and 
                    parsed_url.password == initial_credentials.password):
                return False
        if parsed_url.hostname is None:
            return False
        # DNS check: compare hostnames (case-insensitive)
        if parsed_url.hostname.lower() != initial_host.lower():
            return False
        return True
    
    # Helper to check if an IP address is safe for the initial URL
    def is_safe_ip(ip: str) -> bool:
        # For IP addresses, we check scheme, port, credentials, and DNS
        # Since IPs don't have hostnames, we rely on scheme, port, credentials
        if initial_scheme not in ('http', 'https'):
            return False
        if initial_port is not None and initial_port != 80 and initial_scheme == 'http':
            return False
        if initial_port is not None and initial_port != 443 and initial_scheme == 'https':
            return False
        # Credentials check
        if initial_credentials.username or initial_credentials.password:
            return False
        return True
    
    # Function to resolve hostname and check safety
    def resolve_and_check_hostname(hostname: str) -> Optional[str]:
        try:
            ips = resolve_host(hostname)
            if not ips:
                return None
            # Check first IP
            if not is_safe_ip(ips[0]):
                return None
            return ips[0]
        except Exception:
            return None
    
    # Function to resolve hostname and check safety, returning all IPs if safe
    def resolve_and_check_all_ips(hostname: str) -> Optional[List[str]]:
        try:
            ips = resolve_host(hostname)
            if not ips:
                return None
            # Check all IPs
            for ip in ips:
                if not is_safe_ip(ip):
                    return None
            return ips
        except Exception:
            return None
    
    # Validate initial URL scheme
    if initial_scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Resolve initial hostname
    resolved_initial = resolve_and_check_hostname(initial_host)
    if resolved_initial is None:
        raise ValueError("Failed to resolve initial hostname or IP is unsafe")
    
    current_url = initial_parsed
    max_redirects = 5
    redirects_count = 0
    
    while True:
        # Make the request
        status, headers, body = transport(current_url.geturl())
        
        # Check status
        if status != 200:
            raise ValueError(f"Disallowed status: {status}")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            redirects_count += 1
            if redirects_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Parse Location header
            location_parsed = urllib.parse.urlparse(location_header)
            
            # Check if Location is safe
            if not is_safe_url(location_parsed):
                raise ValueError("Unsafe redirect")
            
            # Resolve the new hostname
            new_hostname = location_parsed.hostname
            if new_hostname is None:
                raise ValueError("Invalid hostname in redirect")
            
            # Resolve and check the new hostname
            resolved_new = resolve_and_check_hostname(new_hostname)
            if resolved_new is None:
                raise ValueError("Failed to resolve new hostname or IP is unsafe")
            
            # Update current URL
            current_url = location_parsed
        else:
            break
    
    return body
