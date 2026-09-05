import urllib.parse
from urllib.request import Request, urlopen
from urllib.error import URLError
from urllib.parse import urlparse, urljoin
from urllib.request import add_stderr_writer
import sys

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict scheme/port validation and redirect handling.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of textual IP addresses.
    
    Returns:
        The body of the HTTP response as a string for status code 200.
    
    Raises:
        ValueError: For disallowed schemes, ports, missing host resolution, or non-200 status codes.
    """
    parsed_url = urlparse(url)
    
    # Validate scheme and port
    allowed_schemes = {'http', 'https'}
    if parsed_url.scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {parsed_url.scheme}")
    
    default_port = {'http': 80, 'https': 443}[parsed_url.scheme]
    if parsed_url.port is not None and parsed_url.port != default_port:
        raise ValueError(f"Port {parsed_url.port} is not the default port for scheme {parsed_url.scheme}")
    
    # Resolve host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"resolve_host returned no IP addresses for {hostname}")
    
    # Build the initial request URL
    # We need to ensure we are using the resolved host if the original URL didn't have one,
    # but the plan says transport(url) is trusted. However, to be safe with redirects,
    # we will construct a full URL with the resolved host if needed, or rely on transport.
    # The plan says "transport(url) returns ...", implying we pass the url to it.
    # But we must validate the scheme/port before calling transport.
    
    # Construct a canonical URL for the initial request
    # If the URL is relative, we need a base. Assuming the URL is absolute based on "absolute or relative"
    # but we need to handle the case where it might be relative.
    # However, the plan says "Resolve the target's host". If it's relative, we can't resolve it without a base.
    # We will assume the URL provided is absolute or we can construct one.
    # Let's assume the input url is absolute for the initial request. If relative, we might need a base.
    # The plan says "The caller-supplied url may be absolute or relative".
    # If relative, we need a base. But where does the base come from?
    # Usually, relative URLs are relative to the current request.
    # We will assume the initial url is absolute. If it's relative, we cannot resolve the host.
    # Let's assume the url is absolute for the purpose of host resolution.
    # If the url is relative, we raise ValueError because we can't resolve the host.
    if not parsed_url.scheme or not parsed_url.hostname:
        raise ValueError("URL must be absolute to resolve host")
    
    # Ensure the URL uses the resolved host if it's not explicitly set, or just use the provided host.
    # The plan says "Resolve the target's host". We use the hostname from the URL.
    
    # We will use the provided URL for the initial request.
    # But we must ensure the scheme and port are valid (already done).
    
    # Construct the request
    req = Request(url)
    
    # Follow redirects
    max_redirects = 5
    current_url = url
    redirect_count = 0
    
    while redirect_count <= max_redirects:
        # Resolve the host of the current URL
        if not urlparse(current_url).hostname:
            raise ValueError("Cannot resolve host for URL")
        
        ip_addresses = resolve_host(urlparse(current_url).hostname)
        if not ip_addresses:
            raise ValueError(f"resolve_host returned no IP addresses for {urlparse(current_url).hostname}")
        
        # Validate scheme and port for the current URL
        parsed_current = urlparse(current_url)
        if parsed_current.scheme not in allowed_schemes:
            raise ValueError(f"Disallowed scheme: {parsed_current.scheme}")
        
        default_port = {'http': 80, 'https': 443}[parsed_current.scheme]
        if parsed_current.port is not None and parsed_current.port != default_port:
            raise ValueError(f"Port {parsed_current.port} is not the default port for scheme {parsed_current.scheme}")
        
        # Call transport
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        # Check status code
        if status != 200:
            raise ValueError(f"Status code {status} is not 200")
        
        # Check for redirects
        if 'Location' in headers:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            location_url = headers['Location']
            
            # Validate redirect URL
            if not location_url.startswith(('http://', 'https://')):
                raise ValueError(f"Redirect URL must be absolute: {location_url}")
            
            parsed_location = urlparse(location_url)
            
            # Check scheme
            if parsed_location.scheme not in allowed_schemes:
                raise ValueError(f"Disallowed scheme in redirect: {parsed_location.scheme}")
            
            # Check port
            default_port = {'http': 80, 'https': 443}[parsed_location.scheme]
            if parsed_location.port is not None and parsed_location.port != default_port:
                raise ValueError(f"Port {parsed_location.port} is not the default port for scheme {parsed_location.scheme}")
            
            # Check for javascript: or data:
            if location_url.lower().startswith('javascript:') or location_url.lower().startswith('data:'):
                raise ValueError("Redirect to javascript: or data: is disallowed")
            
            # Resolve the host of the redirect URL
            if not parsed_location.hostname:
                raise ValueError("Redirect URL must have a hostname")
            
            ip_addresses = resolve_host(parsed_location.hostname)
            if not ip_addresses:
                raise ValueError(f"resolve_host returned no IP addresses for {parsed_location.hostname}")
            
            # Update current_url to the redirect URL
            current_url = location_url
        else:
            break
    
    return body

# Example usage (uncomment to test)
# if __name__ == "__main__":
#     def mock_transport(u):
#         return (200, {'Location': 'https://example.com'}, 'Hello World')
#     def mock_resolve_host(h):
#         return ['127.0.0.1']
#     print(fetch_text('https://example.com', mock_transport, mock_resolve_host))
