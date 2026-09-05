import socket
import urllib.parse
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with security validations.
    
    Args:
        url: The URL to fetch from.
        transport: A callable that returns (status, headers, body) for a given URL.
        resolve_host: A callable that returns textual IP addresses for a hostname.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the request is disallowed based on scheme, port, path, or DNS.
    """
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # GUARD: Check scheme and port
    default_port_http = 80
    default_port_https = 443
    
    if scheme == 'http' and port != default_port_http:
        raise ValueError("HTTP requests must use port 80")
    if scheme == 'https' and port != default_port_https:
        raise ValueError("HTTPS requests must use port 443")
    
    # Validate the URL path doesn't escape the root (no .. segments)
    if parsed_url.path:
        # Remove leading slash if present for normalization
        path = parsed_url.path.lstrip('/')
        # Check for .. segments
        if '..' in path or path.startswith('..'):
            raise ValueError("Path contains invalid .. segments")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    # GUARD: Check DNS segment
    for ip in ip_addresses:
        if ip.startswith('.'):
            raise ValueError(f"DNS segment detected in IP: {ip}")
    
    # Check for redirects (at most 5 hops)
    redirect_count = 0
    current_url = url
    
    while redirect_count < 5:
        # Check if current_url is an absolute URL
        if not current_url.startswith(('http://', 'https://')):
            # If it's not absolute, treat it as relative to the base, but for this spec,
            # we assume the input is absolute or we handle it via transport.
            # The spec says "may be absolute", so we proceed.
            pass
        
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Handle redirects
        if 'location' in headers:
            location = headers['location']
            # Join the requested URL with the referring URL (current_url)
            # If current_url is absolute, use it as base; otherwise, use the last part of the path
            # For simplicity in this context, we assume current_url is the base if absolute,
            # or we just use the location as is if it's absolute.
            
            # Parse the location
            try:
                redirect_url = urllib.parse.urlparse(location)
            except Exception:
                raise ValueError("Invalid redirect URL")
            
            # If the redirect URL is absolute, use it directly
            if redirect_url.scheme:
                current_url = location
            else:
                # Join with the referring URL (current_url)
                # We need to handle the path carefully to avoid double slashes
                if current_url.startswith(('http://', 'https://')):
                    base_path = current_url.split('?', 1)[0]
                    # Remove trailing slash if present
                    if base_path.endswith('/'):
                        base_path = base_path[:-1]
                    if not base_path.endswith('/'):
                        base_path += '/'
                    new_path = urllib.parse.urljoin(base_path, location)
                    current_url = new_path
                else:
                    raise ValueError("Invalid URL format")
            
            redirect_count += 1
        else:
            raise ValueError(f"Unexpected status code: {status}")
    
    raise ValueError("Too many redirects")
