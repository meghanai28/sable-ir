import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict safety checks.
    
    Args:
        url: The URL to fetch (absolute, may contain query parameters).
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the response for status 200.
    
    Raises:
        ValueError: If the request is not HTTPS on the default port,
                   if the resolved IP does not match the target's family,
                   or if the status is not 200.
    """
    parsed = urlparse(url)
    
    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    # Check port (default for HTTP is 80, HTTPS is 443)
    port = parsed.port
    if scheme == 'http':
        if port != 80:
            raise ValueError(f"HTTP request must be on port 80, got {port}")
    elif scheme == 'https':
        if port != 443:
            raise ValueError(f"HTTPS request must be on port 443, got {port}")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    # Resolve hostname
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    # Validate IP format and check against target's family
    target_family = parsed.scheme
    valid_ips = []
    
    for ip in ip_addresses:
        try:
            ip_obj = socket.inet_aton(ip)
            # Check if the IP matches the expected family (IPv4 for http/https)
            if target_family == 'http':
                if ip_obj[0] != 0 and ip_obj[1] != 0 and ip_obj[2] != 0 and ip_obj[3] != 0:
                    valid_ips.append(ip)
            elif target_family == 'https':
                if ip_obj[0] != 0 and ip_obj[1] != 0 and ip_obj[2] != 0 and ip_obj[3] != 0:
                    valid_ips.append(ip)
        except socket.error:
            continue
    
    if not valid_ips:
        raise ValueError(f"No valid IP addresses found for {hostname}")
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
