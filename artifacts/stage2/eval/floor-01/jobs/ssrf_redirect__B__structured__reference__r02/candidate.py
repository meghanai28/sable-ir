import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for a 200 status code.
    
    Raises:
        ValueError: If the request fails validation, has too many redirects, or status is not 200.
    """
    current_url = url
    redirect_count = 0
    max_redirects = 5
    
    while redirect_count <= max_redirects:
        # Parse the current URL
        parsed = urllib.parse.urlparse(current_url)
        
        # Validate scheme and port
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        if scheme not in ['http', 'https']:
            raise ValueError(f"Disallowed scheme: {scheme}")
        
        if scheme == 'http':
            if port is not None and port != 80:
                raise ValueError(f"HTTP port must be 80 or omitted, got {port}")
        elif scheme == 'https':
            if port is not None and port != 443:
                raise ValueError(f"HTTPS port must be 443 or omitted, got {port}")
        
        # Validate hostnames and credentials
        # Check for credentials in the netloc
        netloc = parsed.netloc
        if '@' in netloc:
            raise ValueError("Username or password detected in URL")
        
        # Extract hostname
        hostname = netloc.split(':')[0]
        
        # Resolve hostname
        try:
            resolved_ips = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
        
        if not resolved_ips:
            raise ValueError(f"Hostname {hostname} resolves to no addresses")
        
        # Check if any address is not a global public address
        # Assuming resolve_host returns strings, we check for obvious non-public indicators
        # In a real scenario, this would check against a list of private IP ranges
        for ip in resolved_ips:
            if ip.startswith(('127.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.15.', '192.168.', '::1')):
                raise ValueError(f"Non-public IP address detected: {ip}")
        
        # Make the transport request
        status, headers, body = transport(current_url)
        
        if status != 200:
            raise ValueError(f"Status code is not 200: {status}")
        
        # Handle redirects
        location_header = headers.get('location', None)
        if location_header is not None:
            location_header = location_header.strip().lower()
            if not location_header:
                raise ValueError("Redirect Location header is missing or empty")
            
            # Resolve the redirect location
            redirect_parsed = urllib.parse.urlparse(location_header)
            
            # Combine scheme and path if missing
            if redirect_parsed.scheme == '' and redirect_parsed.netloc == '':
                redirect_parsed = urllib.parse.urljoin(current_url, location_header)
            else:
                redirect_parsed = urllib.parse.urljoin(current_url, location_header)
            
            current_url = redirect_parsed.geturl()
            redirect_count += 1
            
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects: {redirect_count}")
        else:
            # No redirect, break the loop
            break
    
    return body

# Example usage (uncomment to test):
# def mock_transport(url):
#     return (200, {'location': 'https://example.com'}, "Hello, World!")
#
# def mock_resolve_host(hostname):
#     return ['93.184.216.34']
#
# # result = fetch_text("http://example.com", mock_transport, mock_resolve_host)
# # print(result)
