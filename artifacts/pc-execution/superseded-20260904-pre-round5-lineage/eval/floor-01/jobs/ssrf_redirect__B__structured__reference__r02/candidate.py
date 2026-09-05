import socket
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    current_url = url
    redirect_count = 0
    
    while True:
        # Parse the current URL to extract components
        parsed = urllib.parse.urlparse(current_url)
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        port = parsed.port
        path = parsed.path
        
        # Validate scheme
        if scheme not in ['http', 'https']:
            raise ValueError("Disallowed scheme")
        
        # Validate port if provided
        if port is not None:
            if scheme == 'http' and port != 80:
                raise ValueError("Invalid port for HTTP")
            if scheme == 'https' and port != 443:
                raise ValueError("Invalid port for HTTPS")
        
        # Validate hostname
        if not host:
            raise ValueError("Invalid hostname")
        
        # Resolve hostname
        try:
            addresses = resolve_host(host)
        except Exception:
            raise ValueError("Failed to resolve hostname")
        
        if not addresses:
            raise ValueError("Hostname does not resolve to any address")
        
        # Check if addresses are public (simplified check: assume non-private ranges are public for this context, 
        # but strictly speaking, we should block 10.x, 172.16-31.x, 192.168.x, 127.x, ::1, etc.)
        is_public = True
        for addr in addresses:
            # Basic check for private IPs
            if addr.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.', '127.', '::1', 'fc00::/7')):
                is_public = False
                break
        if not is_public:
            raise ValueError("Non-public address")
        
        # Make the request
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirects
        if status in [301, 302, 303, 307, 308]:
            redirect_count += 1
            if redirect_count > 5:
                raise ValueError("Too many redirects")
            
            location_header = headers.get('Location', None)
            if not location_header:
                raise ValueError("Missing Location header")
            
            # Resolve the redirect location
            redirect_url = urllib.parse.urljoin(current_url, location_header)
            current_url = redirect_url
            
            # Re-validate the new destination
            # The loop will handle the re-validation logic again
        else:
            raise ValueError("Unexpected status code")

    raise ValueError("Unexpected error")
