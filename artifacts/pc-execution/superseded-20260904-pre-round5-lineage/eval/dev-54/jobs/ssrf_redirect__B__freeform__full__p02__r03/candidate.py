import socket
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Tuple, List, Optional

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed or invalid.
    """
    # Parse the initial URL
    parsed_url = urlparse(url)
    
    # Determine the scheme and port
    scheme = parsed_url.scheme.lower()
    default_port = None
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Check if the port matches the default port
    if parsed_url.port is not None and parsed_url.port != default_port:
        raise ValueError(f"Non-default port {parsed_url.port} not allowed for scheme {scheme}")
    
    # Resolve the host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"No valid IP addresses found for {hostname}")
    
    # Validate IP addresses
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
        except socket.error:
            raise ValueError(f"Invalid IP address: {ip}")
    
    # Determine the base URL for relative redirects
    base_url = parsed_url.geturl()
    
    # Track the number of hops
    hop_count = 0
    current_url = base_url
    
    while True:
        # Fetch the response
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Maximum number of redirects (5) exceeded")
            
            # Resolve the Location header
            location_url = location_header
            
            # If the Location is relative, join it with the current URL
            if not parsed_url.scheme:
                location_url = urljoin(current_url, location_header)
            
            # Parse the new URL
            new_parsed_url = urlparse(location_url)
            
            # Check if the scheme is valid
            if new_parsed_url.scheme.lower() != scheme:
                raise ValueError(f"Scheme mismatch: {new_parsed_url.scheme} != {scheme}")
            
            # Check if the port matches the default port for the scheme
            if new_parsed_url.port is not None:
                if new_parsed_url.port != default_port:
                    raise ValueError(f"Non-default port {new_parsed_url.port} not allowed")
            
            # Check if the DNS/public-address matches
            new_hostname = new_parsed_url.hostname
            if not new_hostname:
                raise ValueError("No hostname in redirected URL")
            
            new_ip_addresses = resolve_host(new_hostname)
            if not new_ip_addresses:
                raise ValueError(f"No valid IP addresses found for {new_hostname}")
            
            for new_ip in new_ip_addresses:
                try:
                    socket.inet_aton(new_ip)
                except socket.error:
                    raise ValueError(f"Invalid IP address: {new_ip}")
            
            # Check if the IP addresses match the original resolved IPs
            if set(new_ip_addresses) != set(ip_addresses):
                raise ValueError("DNS/public-address mismatch")
            
            # Update the current URL
            current_url = new_parsed_url.geturl()
            hostname = new_hostname
            ip_addresses = new_ip_addresses
        else:
            # No Location header, exit the loop
            break
    
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
