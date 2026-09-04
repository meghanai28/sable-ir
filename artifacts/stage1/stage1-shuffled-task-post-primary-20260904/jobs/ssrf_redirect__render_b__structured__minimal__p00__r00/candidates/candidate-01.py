import os

def fetch_text(url, transport, resolve_host):
    # Parse URL to extract scheme, host, port, and path
    if '://' not in url:
        raise ValueError("Invalid URL: missing scheme")
    
    scheme, rest = url.split('://', 1)
    
    if scheme not in ('http', 'https'):
        raise ValueError("Invalid URL: only HTTP and HTTPS are allowed")
    
    # Determine default port
    default_port = 443 if scheme == 'https' else 80
    
    # Extract host and path
    if '/' in rest:
        host_port, path = rest.split('/', 1)
        path = '/' + path
    else:
        host_port = rest
        path = '/'
    
    # Parse host and port
    if ':' in host_port:
        host, port_str = host_port.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError("Invalid port")
    else:
        host = host_port
        port = default_port
    
    # Validate port
    if port != default_port:
        raise ValueError("Invalid port: only default port allowed")
    
    # Resolve host to IP addresses
    ip_addresses = resolve_host(host)
    
    # Validate that host resolves to something
    if not ip_addresses:
        raise ValueError("Host could not be resolved")
    
    # Reconstruct URL for transport (with original host for Host header compatibility)
    transport_url = f"{scheme}://{host_port}{path}"
    
    # Make the request
    status, headers, body = transport(transport_url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body as string (transport should return bytes, decode to str)
    if isinstance(body, bytes):
        return body.decode('utf-8')
    return str(body)
