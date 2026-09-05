import socket
from urllib.parse import urlparse

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL using the provided transport and hostname resolver.
    
    Args:
        url: The URL to fetch (absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not HTTP/HTTPS, port is not default, or status is not 200.
    """
    parsed = urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port
    port = parsed.port
    if port is None:
        port = 80 if parsed.scheme == 'http' else 443
    
    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("No hostname found in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Failed to resolve hostname")
    
    # Use the first resolved IP
    ip = ip_addresses[0]
    
    # Create connection and fetch
    try:
        conn = socket.create_connection((ip, port), timeout=5)
        http_conn = conn.makefile('rb')
        
        # Read status line
        status_line = http_conn.readline().decode('utf-8').strip()
        parts = status_line.split(' ')
        if not parts:
            raise ValueError("Invalid status line")
        
        status_code = int(parts[0])
        
        if status_code != 200:
            raise ValueError(f"Disallowed status code: {status_code}")
        
        # Read headers until empty line
        headers = {}
        while True:
            line = http_conn.readline().decode('utf-8').strip()
            if not line:
                break
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Read body
        body = b''
        while True:
            chunk = http_conn.read(8192)
            if not chunk:
                break
            body += chunk
        
        return body.decode('utf-8')
        
    except Exception as e:
        raise ValueError(f"Failed to fetch: {str(e)}")
