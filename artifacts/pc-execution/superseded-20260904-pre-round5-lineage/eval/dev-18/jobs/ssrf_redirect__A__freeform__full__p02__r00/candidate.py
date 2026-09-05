import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL to extract scheme, netloc, path, and query
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.netloc
    path = parsed.path
    query = parsed.query

    # Validate scheme: only HTTP and HTTPS on default ports are allowed
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    # Determine the port
    if scheme == 'http':
        port = 80
    elif scheme == 'https':
        port = 443
    else:
        raise ValueError("Invalid scheme")

    # Construct the full URL to use with urllib for parsing, but we will manually handle the connection
    # We need to resolve the hostname to IP addresses
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Could not resolve hostname: {hostname}")

    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {hostname}")

    # Use the first resolved IP address for the connection
    resolved_ip = ip_addresses[0]

    # Build the full URL string for the request
    # If path is empty, ensure we have a valid path
    if not path:
        path = '/'
    
    full_url = f"{scheme}://{hostname}{path}"
    if query:
        full_url += f"?{query}"

    # Create the request using urllib which handles the TCP connection
    # We will pass the full_url to urllib.request.urlopen but we need to ensure we don't follow redirects
    # However, urllib.request.urlopen follows redirects by default. We need to disable that.
    # Also, we need to ensure we are connecting to the resolved IP. urllib uses the hostname from the URL.
    # To strictly follow the plan "bind to the resolved address", we might need to use a custom HTTPConnection.
    # But the plan says "transport(url) returns...", implying we use the provided transport.
    # The plan says "Resolve the hostname to IP addresses via resolve_host and bind to the resolved address".
    # This implies we should construct a socket connection to the resolved IP.
    
    # Let's implement a raw socket connection to be safe and strictly follow "bind to the resolved address".
    # We will create a custom HTTP client that connects directly to the resolved IP.

    # Create a socket connection
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    # Connect to the resolved IP and port
    try:
        sock.connect((resolved_ip, port))
    except socket.gaierror:
        sock.close()
        raise ValueError(f"Could not connect to resolved IP: {resolved_ip}")
    except socket.timeout:
        sock.close()
        raise ValueError(f"Connection timeout to {resolved_ip}")

    # Prepare the request line
    request_line = f"GET {path}?{query} HTTP/1.1\r\n"
    
    # Prepare headers
    headers = [
        "Host: " + hostname,
        "User-Agent: Python-urllib/1.0",
        "Accept: */*",
        "Connection: close"
    ]
    
    # Add headers to the request
    request_body = request_line + "\r\n".join(headers) + "\r\n\r\n"
    
    # Send the request
    sock.sendall(request_body.encode('utf-8'))
    
    # Receive the response
    response = b""
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        except socket.timeout:
            break
    
    # Parse the response
    lines = response.split(b'\r\n')
    
    # Find the status line
    status_line_idx = -1
    for i, line in enumerate(lines):
        if line.startswith(b'HTTP/'):
            status_line_idx = i
            break
    
    if status_line_idx == -1:
        sock.close()
        raise ValueError("Invalid HTTP response format")
    
    # Parse status line
    status_line_str = lines[status_line_idx].decode('utf-8')
    # Example: HTTP/1.1 200 OK
    parts = status_line_str.split(' ')
    if len(parts) < 2:
        sock.close()
        raise ValueError("Invalid HTTP status line")
    
    status_code = int(parts[1])
    
    # Check status code
    if status_code != 200:
        sock.close()
        raise ValueError(f"Request failed with status code: {status_code}")
    
    # Find the body (after headers)
    # Headers end with a blank line (two consecutive \r\n)
    body_start_idx = -1
    header_lines = []
    for i in range(status_line_idx + 1, len(lines)):
        line = lines[i]
        if line == b'\r\n':
            body_start_idx = i + 1
            break
        header_lines.append(line)
    
    if body_start_idx == -1:
        # If no body found, check if we reached end of list
        # If the last line is empty, it might be the end
        if lines and lines[-1] == b'\r\n':
            body_start_idx = len(lines)
        else:
            sock.close()
            raise ValueError("No body found in response")
    
    # Extract body
    body = response[body_start_idx:]
    
    # Decode the body
    try:
        body_str = body.decode('utf-8')
    except UnicodeDecodeError:
        # Try to decode with errors='ignore' or 'replace' if utf-8 fails
        body_str = body.decode('utf-8', errors='replace')
    
    sock.close()
    return body_str
