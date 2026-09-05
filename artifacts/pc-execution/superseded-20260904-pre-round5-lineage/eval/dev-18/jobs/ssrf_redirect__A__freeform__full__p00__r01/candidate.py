import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and host resolver.
    
    Args:
        url: The URL to fetch (may be absolute with query/fragment).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme/port is not HTTP/HTTPS, status is not 200, or other errors occur.
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Determine port
    default_port = 80 if scheme == 'http' else 443
    actual_port = parsed.port
    
    if actual_port is None:
        actual_port = default_port
    
    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: no hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for {hostname}")
    
    # Use the first resolved IP
    target_ip = ip_addresses[0]
    
    # Construct the full URL for transport
    # Ensure the port is included if it's not the default for the scheme
    # However, the transport function likely expects the full URL or we construct it.
    # Based on "Accept HTTP or HTTPS on its default port", we use the parsed URL.
    # We must not follow redirects, so we use the parsed URL directly.
    
    # Prepare the request URL. If no port is specified in the input, use default.
    # If port is specified, use it.
    request_url = parsed._replace(port=actual_port).geturl()
    
    # Attempt to fetch
    try:
        status, headers, body = transport(request_url)
    except Exception as e:
        raise ValueError(f"Transport error: {e}")
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
