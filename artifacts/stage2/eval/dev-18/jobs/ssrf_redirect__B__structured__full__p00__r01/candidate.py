import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    # Guard: Check scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Unknown scheme")
    
    if port is not None and port != default_port:
        raise ValueError("Non-default port")
    
    # Resolve hostname
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Hostname resolution failed")
    
    if not ip_addresses:
        raise ValueError("No IP address resolved")
    
    # Prepare the request
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Python-urllib')
    
    # Process redirects
    hops = 0
    current_url = url
    
    while True:
        # Check redirect limit
        if hops > 5:
            raise ValueError("Redirect limit exceeded")
        
        # Create connection
        context = ssl._create_unverified_context()
        conn = socket.create_connection((ip_addresses[0], parsed.port if port is None else port), context=context)
        
        # Read headers and body
        headers = {}
        status_line = conn.recv(4096).decode('utf-8').strip()
        parts = status_line.split(' ')
        status_code = int(parts[1])
        
        # Parse headers
        while True:
            header_line = conn.recv(4096).decode('utf-8').strip()
            if not header_line:
                break
            if ':' in header_line:
                key, value = header_line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        # Check status
        if status_code == 200:
            break
        elif status_code == 301 or status_code == 302:
            # Check if there's a Location header
            location_header = headers.get('location')
            if not location_header:
                raise ValueError("Redirect without Location header")
            
            # Check redirect URL scheme and port
            try:
                redirect_url = urllib.parse.urlparse(location_header)
                redirect_scheme = redirect_url.scheme.lower()
                redirect_port = redirect_url.port
                
                if redirect_scheme != scheme:
                    raise ValueError("Redirect to different scheme")
                
                if redirect_port is not None and redirect_port != default_port:
                    raise ValueError("Redirect to non-default port")
                
                # Check for javascript: or data:
                if location_header.startswith('javascript:') or location_header.startswith('data:'):
                    raise ValueError("Disallowed redirect target")
                
                # Update current URL
                current_url = location_header
                hops += 1
                continue
            except Exception:
                raise ValueError("Invalid redirect URL")
        else:
            raise ValueError(f"Unexpected status code: {status_code}")
    
    # Read body
    body = b''
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        body += chunk
    
    conn.close()
    
    return body.decode('utf-8')
