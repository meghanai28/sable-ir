import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    
    # GUARD: Check scheme is http or https
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed request: scheme must be http or https")
    
    # Extract hostname
    hostname = parsed.netloc
    if not hostname:
        raise ValueError("Disallowed request: missing hostname")
    
    # Remove port from hostname if present for resolution
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    
    # GUARD: Resolve hostname
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Disallowed request: could not resolve hostname")
    
    # Determine port based on scheme
    port = 80 if scheme == 'http' else 443
    
    # Create socket and connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)  # Prevent hanging indefinitely
    
    # Connect to one of the resolved IPs
    for ip in ip_addresses:
        try:
            sock.connect((ip, port))
            break
        except (socket.timeout, socket.error, ConnectionRefusedError):
            continue
    else:
        raise ValueError("Disallowed request: could not connect to server")
    
    # Send request (basic GET)
    request_path = parsed.path if parsed.path else '/'
    request = f"GET {request_path} HTTP/1.1\r\nHost: {hostname}\r\n\r\n"
    sock.send(request.encode('utf-8'))
    
    # Read response
    response = b""
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        except (socket.timeout, socket.error):
            break
    
    sock.close()
    
    # Parse response lines to find status code
    lines = response.split(b'\r\n')
    status_line = lines[0].decode('utf-8')
    
    # Extract status code (e.g., "HTTP/1.1 200 OK")
    parts = status_line.split()
    if len(parts) < 2:
        raise ValueError("Disallowed request: invalid response status")
    
    status_code = int(parts[1])
    
    # ORDER: Return body only for status 200
    if status_code == 200:
        # Skip status line and headers to get body
        body_start = 2
        body = response[body_start:].decode('utf-8')
        return body
    else:
        raise ValueError("Disallowed request: status code is not 200")
