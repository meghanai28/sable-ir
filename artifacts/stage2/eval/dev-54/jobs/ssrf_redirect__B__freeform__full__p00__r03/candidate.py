import urllib.parse
import socket
import re

def fetch_text(url, transport, resolve_host):
    """
    Fetches text from a URL with strict validation and redirection limits.
    
    Args:
        url: The initial URL to fetch from (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the HTTP response with status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP is found, or unsafe redirects occur.
    """
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {parsed.scheme}")
    
    # Resolve the initial hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    current_url = parsed
    max_redirects = 5
    redirect_count = 0
    
    while redirect_count <= max_redirects:
        # Prepare the request URL
        request_url = current_url
        
        # Determine the scheme and port for validation
        scheme = current_url.scheme
        port = current_url.port
        if port is None:
            if scheme == 'http':
                port = 80
            elif scheme == 'https':
                port = 443
        
        # Fetch the response
        status, headers, body = transport(request_url)
        
        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects: {redirect_count}")
            
            # Parse the Location header
            redirect_url = urllib.parse.urlparse(location_header)
            
            # Check if the redirect is absolute
            if not redirect_url.scheme:
                # Relative URL, resolve against current URL
                redirect_url = urllib.parse.urljoin(request_url, location_header)
                redirect_url = urllib.parse.urlparse(redirect_url)
            
            # Validate scheme and port
            if redirect_url.scheme != scheme or (redirect_url.port != port and redirect_url.port is not None):
                raise ValueError(f"Redirect scheme or port mismatch: {redirect_url.scheme}:{redirect_url.port} vs {scheme}:{port}")
            
            # Validate DNS resolution for the new hostname
            new_hostname = redirect_url.hostname
            if not new_hostname:
                raise ValueError(f"Invalid hostname in redirect: {redirect_url.netloc}")
            
            new_ip_addresses = resolve_host(new_hostname)
            if not new_ip_addresses:
                raise ValueError(f"No IP addresses found for hostname in redirect: {new_hostname}")
            
            # Validate public address (basic check for IPv4/IPv6 format)
            if not is_valid_public_address(new_ip_addresses[0]):
                raise ValueError(f"Invalid public address in redirect: {new_ip_addresses[0]}")
            
            # Update current URL
            current_url = redirect_url
        else:
            break
    
    return body

def is_valid_public_address(ip_str):
    """
    Basic validation to ensure the IP address is in a textual format.
    This is a simplified check; a full RFC 3339 or RFC 5952 validator would be more robust.
    """
    # Check for IPv4 or IPv6 patterns
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    ipv6_pattern = r'^[0-9a-fA-F:]+$'
    
    # Ensure it's not empty
    if not ip_str:
        return False
    
    # Try IPv4
    if re.match(ipv4_pattern, ip_str):
        return True
    
    # Try IPv6
    if re.match(ipv6_pattern, ip_str):
        return True
    
    return False
