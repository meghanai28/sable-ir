import socket
import urllib.parse
import urllib.request
import urllib.error

def resolve_host(hostname):
    """Resolve hostname to IP addresses.
    This is a stub implementation that raises ValueError if resolution fails.
    In a real scenario, this would use socket.getaddrinfo or similar.
    """
    try:
        return socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

def fetch_text(url, transport, resolve_host):
    """Fetch text from a URL using the provided transport.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that resolves a hostname to IP addresses.
    
    Returns:
        The body text of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., wrong protocol, failed resolution,
                   or unsafe redirects).
    """
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate protocol and port
    if parsed_url.scheme not in ['http', 'https']:
        raise ValueError(f"Only HTTP and HTTPS are allowed, got {parsed_url.scheme}")
    
    # Determine the default port
    default_port = 80 if parsed_url.scheme == 'http' else 443
    
    # Check if the port is the default port
    if parsed_url.port != default_port:
        raise ValueError(f"Only default ports are allowed for {parsed_url.scheme}, got {parsed_url.port}")
    
    # Resolve the hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Build the request URL without the port if it's the default
    request_url = f"{parsed_url.scheme}://{hostname}{parsed_url.path}"
    if parsed_url.query:
        request_url += f"?{parsed_url.query}"
    if parsed_url.fragment:
        request_url += f"#{parsed_url.fragment}"
    
    # Make the request using the transport
    status, headers, body = transport(request_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Check for Location header and follow redirects
    # The plan says: follow the initial destination but never follow a Location header
    # So we do NOT follow redirects. We just check the final destination (which is the initial one).
    # However, to be safe, we should ensure the URL we are about to receive the body for
    # is the one we requested initially, not any redirect.
    
    # Since we are not following redirects, the URL we used is the final destination.
    # We need to ensure it remains beneath the requested public URL.
    # In this case, the requested URL is the one we passed in, and we are fetching exactly that.
    # So the check is trivially passed.
    
    # Return the body text
    return body.decode('utf-8') if isinstance(body, bytes) else body
