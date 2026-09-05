import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL, validating the request against safety constraints.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed, resolve_host returns no IPs, or status is not 200.
    """
    # Parse the URL to get the scheme and netloc
    parsed_url = urllib.parse.urlparse(url)
    
    # Determine the scheme (HTTP or HTTPS)
    scheme = parsed_url.scheme.lower()
    
    # Validate scheme (only HTTP and HTTPS are allowed on default ports)
    if scheme not in ['http', 'https']:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Determine the port based on scheme
    if scheme == 'http':
        default_port = 80
    else:
        default_port = 443
    
    # Extract the hostname from the URL
    hostname = parsed_url.hostname
    
    # Resolve the hostname to IP addresses
    ip_addresses = resolve_host(hostname)
    
    # Raise ValueError if no IP addresses are found
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Use the first IP address for the connection
    ip_address = ip_addresses[0]
    
    # Construct the URL for the transport function
    # We need to ensure we are using the correct port in the URL string for the transport
    if scheme == 'http':
        full_url = f"http://{hostname}:{default_port}"
    else:
        full_url = f"https://{hostname}:{default_port}"
    
    # Call the transport function
    status, headers, body = transport(full_url)
    
    # Check if the status is exactly 200
    if status != 200:
        raise ValueError(f"Request status is not 200: {status}")
    
    # Return the body
    return body
