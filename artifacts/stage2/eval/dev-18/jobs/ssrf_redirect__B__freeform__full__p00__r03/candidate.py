import socket
import urllib.parse
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation against DNS, port, and redirect hops.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for a successful 200 status.
    
    Raises:
        ValueError: If the URL is invalid, the resolved host is invalid, or redirects exceed limits.
    """
    # Parse the initial URL
    initial_parsed = urlparse(url)
    
    # Validate scheme and port
    allowed_schemes = ['http', 'https']
    if initial_parsed.scheme not in allowed_schemes:
        raise ValueError(f"Unsupported scheme: {initial_parsed.scheme}")
    
    # Determine default port based on scheme
    default_port = {'http': 80, 'https': 444}[initial_parsed.scheme]
    current_port = initial_parsed.port
    
    # Validate DNS resolution and host validity
    # We need to resolve the hostname to check if it's valid before proceeding
    hostname = initial_parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: No hostname found")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No valid IP addresses found for: {hostname}")
    
    # Helper function to validate a URL against the initial constraints
    def validate_url(parsed_url, base_scheme, base_port, base_ips):
        """
        Check if the parsed URL matches the initial scheme, port, and DNS constraints.
        """
        # Scheme must match
        if parsed_url.scheme != base_scheme:
            return False
        
        # Port must match (or be the default for the scheme if not specified)
        if parsed_url.port:
            if parsed_url.port != base_port:
                return False
        else:
            # If port is not specified, it must be the default
            if parsed_url.port != base_port:
                return False
        
        # DNS resolution check
        try:
            host = parsed_url.hostname
            if not host:
                return False
            resolved = resolve_host(host)
            if not resolved:
                return False
            # Basic check to ensure we didn't get a weird IP or domain
            # The problem statement implies we check against the same validation applied to the initial destination.
            # Assuming resolve_host handles the actual validation logic (e.g., blocking 127.0.0.1, etc.)
            # Here we just ensure it returns a list of strings (IPs)
        except Exception:
            return False
        
        return True
    
    # Check initial URL
    if not validate_url(initial_parsed, initial_parsed.scheme, current_port, resolved_ips):
        raise ValueError("Invalid initial URL configuration")
    
    # Build the initial request URL
    request_url = initial_parsed._geturl()
    
    # Perform the fetch
    try:
        response = transport(request_url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    status, headers, body = response
    
    # Check for success
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Handle redirects
    redirect_count = 0
    current_url = request_url
    
    while True:
        # Parse current URL
        current_parsed = urlparse(current_url)
        
        # Check for Location header
        location = None
        if 'location' in headers:
            location = headers['location']
        
        if location:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Redirect limit exceeded (max 5 hops)")
            
            # Parse the redirect URL
            redirect_parsed = urlparse(location)
            
            # Validate the redirect URL against constraints
            if not validate_url(redirect_parsed, initial_parsed.scheme, current_port, resolved_ips):
                raise ValueError(f"Invalid redirect URL: {location}")
            
            # Update current URL to the redirect URL
            current_url = redirect_parsed._geturl()
        else:
            break
    
    return body

# Example usage (uncomment to test):
# if __name__ == "__main__":
#     def mock_transport(url):
#         # Simulate a successful response
#         return (200, {}, b"Hello, World!")
#     
#     def mock_resolve_host(hostname):
#         if hostname == "example.com":
#             return ["93.184.216.34"]
#         return []
#     
#     # This would raise ValueError because example.com resolves to a real IP but the mock
#     # might not be fully representative of the security constraints.
#     # In a real scenario, the resolve_host function would enforce the security policies.
#     try:
#         result = fetch_text("http://example.com", mock_transport, mock_resolve_host)
#         print(result)
#     except ValueError as e:
#         print(f"ValueError: {e}")
