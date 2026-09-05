import socket
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed_url = urlparse(url)
    
    # GUARD: Check scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Disallowed request: scheme not http or https")
    
    # GUARD: Resolve host
    hostname = parsed_url.hostname
    if hostname is None:
        raise ValueError("Disallowed request: no hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("Disallowed request: no IP address resolved for host")
    
    # Determine port based on scheme
    default_port = 80 if parsed_url.scheme == 'http' else 443
    
    # Use the first resolved IP address for the connection
    ip_address = ip_addresses[0]
    
    # Create a socket and connect
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((ip_address, default_port))
        
        # Call transport to get response
        status, headers, body = transport(url)
        
        # ORDER: Return body only for status 200
        if status == 200:
            return body.decode('utf-8')
        else:
            raise ValueError(f"Disallowed request: HTTP status {status} is not 200")
    finally:
        sock.close()
