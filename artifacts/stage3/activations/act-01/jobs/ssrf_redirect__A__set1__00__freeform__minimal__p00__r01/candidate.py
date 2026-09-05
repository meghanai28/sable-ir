import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict validation and no redirects.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https or if status is not 200.
    """
    # Validate scheme
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")
    
    try:
        ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ips:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")
    
    # Select the first IP address
    ip_address = ips[0]
    
    # Build the request URL
    request_url = f"{parsed_url.scheme}://{ip_address}{parsed_url.path}"
    
    # Call transport
    status, headers, body = transport(request_url)
    
    # Validate status code
    if status != 200:
        raise ValueError(f"Status code is not 200: {status}")
    
    # Return body
    return body
