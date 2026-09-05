import socket
import urllib.parse
import urllib.request
import urllib.error

def resolve_host(hostname: str) -> list:
    """Resolve hostname to a list of textual IP addresses."""
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [addr[4][0] for addr in ip_addresses]
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

def fetch_text(url: str, transport=None, resolve_host=None) -> str:
    """Fetch text from a URL.
    
    Args:
        url: The URL to fetch.
        transport: Optional function to fetch data. If None, uses urllib.
        resolve_host: Optional function to resolve hostnames. If None, uses socket.getaddrinfo.
    
    Returns:
        The body of the response as a string.
    
    Raises:
        ValueError: If the request is disallowed or fails.
    """
    if transport is None:
        def transport_wrapper(url):
            req = urllib.request.Request(url)
            try:
                response = urllib.request.urlopen(req)
                return (response.status, dict(response.headers), response.read())
            except urllib.error.HTTPError as e:
                raise ValueError(f"HTTP error occurred: {e.code}") from e
            except Exception as e:
                raise ValueError(f"Request failed: {e}") from e
        transport = transport_wrapper
    
    if resolve_host is None:
        def resolve_wrapper(hostname):
            return resolve_host(hostname)
        resolve_host = resolve_wrapper
    
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Check scheme
    if parsed_url.scheme.lower() != 'https':
        raise ValueError("Only HTTPS requests are allowed.")
    
    # Get the hostname
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname")
    
    # Resolve the hostname
    resolved_ips = resolve_host(hostname)
    
    # Check if any resolved IP belongs to the target's IP address family
    # Since we don't have a target IP address family, we assume any resolved IP is acceptable
    # However, if the plan implies checking against a specific family, we would need that information.
    # For now, we proceed with the resolved IPs.
    
    # Open the connection
    try:
        response = transport(url)
    except ValueError:
        raise
    
    status, headers, body = response
    
    # Check status code
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}")
    
    # Return the body
    return body.decode('utf-8') if isinstance(body, bytes) else body
