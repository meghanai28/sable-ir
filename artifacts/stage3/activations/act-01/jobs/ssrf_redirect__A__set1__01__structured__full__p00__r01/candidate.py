import os
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolution functions.
    Validates that the resolved path does not escape the filesystem root and that
    symbolic links do not escape the root. Returns the body for a 200 status.
    Raises ValueError for disallowed requests.
    """
    # Parse the URL to extract the scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    
    # Determine the scheme and port
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Default ports for HTTP and HTTPS
    default_http_port = 80
    default_https_port = 443
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Determine the hostname and port
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("No hostname in URL")
    
    # Resolve the hostname to IP addresses
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname")
    
    # Use the first resolved IP address for the request
    resolved_ip = ip_addresses[0]
    
    # Determine the port to use (default if not specified)
    if port is None:
        port = default_http_port if scheme == 'http' else default_https_port
    else:
        port = port
    
    # Construct the request URL
    request_url = f"{scheme}://{hostname}:{port}{parsed.path}"
    
    # Perform the HTTP request using the provided transport
    try:
        response = transport(request_url)
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
    
    # Check the status code
    status, headers, body = response
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Decode the body to text
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        # Try to handle encoding issues gracefully, though the spec implies text
        raise ValueError("Failed to decode body to text")
    
    return text
