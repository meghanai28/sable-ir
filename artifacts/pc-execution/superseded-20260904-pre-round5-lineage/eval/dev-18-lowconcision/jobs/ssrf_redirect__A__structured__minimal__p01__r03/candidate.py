import socket
import urllib.parse
import urllib.request
import urllib.error
import http.client

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL with strict security controls.
    
    Args:
        url: The URL to fetch (must not be absolute).
        transport: A callable that returns (status, headers, body) for an HTTP request.
        resolve_host: A callable that returns a list of textual IP addresses for a hostname.
    
    Returns:
        The body of the response as a string if status is 200.
    
    Raises:
        ValueError: If the URL is absolute, the host is unreachable, or redirects are followed.
    """
    # Guard: Reject absolute URLs
    if urllib.parse.urlparse(url).scheme:
        raise ValueError("Absolute URLs are disallowed")
    
    # Parse the URL components
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    port = parsed.port
    path = parsed.path
    
    # Guard: Resolve hostname
    if not hostname:
        raise ValueError("Invalid hostname in URL")
    
    if port is None:
        if "http" in parsed.scheme:
            port = 80
        elif "https" in parsed.scheme:
            port = 443
    
    # Guard: Check if host is reachable
    try:
        if resolve_host(hostname):
            pass
        else:
            raise ValueError(f"Host {hostname} is unreachable")
    except Exception:
        raise ValueError(f"Host {hostname} is unreachable")
    
    # Construct the request URL
    request_url = f"{parsed.scheme}://{hostname}"
    if port:
        request_url += f":{port}"
    if path:
        request_url += path
    
    # Open the connection and get the response
    conn = None
    try:
        # Use urllib.request to handle the transport
        # We need to implement a custom opener that uses the provided transport
        # Since transport(url) returns (status, headers, body), we can't directly use urllib.request.urlopen
        # We will manually construct the request and call the transport function
        
        # Create a socket connection
        if parsed.scheme == "http":
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if port:
                conn.connect((hostname, port))
            else:
                conn.connect((hostname, 80))
        else:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if port:
                conn.connect((hostname, port))
            else:
                conn.connect((hostname, 443))
        
        # Send the request
        request_line = f"GET {request_url} HTTP/1.1\r\n"
        headers = [
            "Host: " + hostname,
            "Connection: close"
        ]
        full_request = request_line + "\r\n".join(headers) + "\r\n\r\n"
        conn.sendall(full_request.encode())
        
        # Read the response
        response_start = b"\r\n\r\n"
        response = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            response += chunk
            if response_start in response:
                break
        
        # Parse the response
        response_bytes = response.split(response_start)
        if len(response_bytes) < 2:
            raise ValueError("Invalid response format")
        
        response_text = response_bytes[1].decode('utf-8', errors='replace')
        lines = response_text.split("\r\n")
        
        # Parse status and headers
        status_parts = lines[0].split(" ")
        if len(status_parts) < 2:
            raise ValueError("Invalid status line")
        
        status_code = int(status_parts[1])
        
        # Parse headers
        headers_dict = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers_dict[key.strip().lower()] = value.strip()
        
        # Guard: Check status code
        if status_code != 200:
            raise ValueError(f"Status code {status_code} is not 200")
        
        # Guard: Never follow redirects
        if "location" in headers_dict:
            raise ValueError("Redirects are disallowed")
        
        # Return the body
        return response_text
        
    except Exception as e:
        if conn:
            conn.close()
        raise ValueError(f"Failed to fetch URL: {str(e)}")
    finally:
        if conn:
            conn.close()
