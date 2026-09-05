import socket
import urllib.parse
import urllib.request
import urllib.error
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL using the provided transport.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if the status is 200.
    
    Raises:
        ValueError: If the request is disallowed or the status is not 200.
    """
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the default port
    default_port = 80 if scheme == 'http' else 443
    
    # Resolve the hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: No hostname found.")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Failed to resolve hostname.")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname.")
    
    # Validate the resolved IP addresses
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
        except socket.error:
            raise ValueError(f"Invalid IP address: {ip}")
    
    # Build the request URL
    request_url = parsed_url._replace(port=default_port if port == default_port else port).geturl()
    
    # Make the request
    try:
        response = transport(request_url)
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    # Check the status
    status, headers, body = response
    
    if status != 200:
        raise ValueError(f"Status code {status} is not allowed.")
    
    return body
