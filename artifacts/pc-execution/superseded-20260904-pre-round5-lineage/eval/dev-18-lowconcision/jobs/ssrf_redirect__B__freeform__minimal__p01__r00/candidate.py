import socket
import urllib.parse
import urllib.request

def resolve_host(hostname):
    """Placeholder for the supplied resolve_host function.
    In a real scenario, this would resolve the hostname to IP addresses.
    For this implementation, we assume it returns a list of IP strings or an empty list.
    """
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [ip[4][0] for ip in ip_addresses]
    except (socket.gaierror, socket.herror):
        return []

def fetch_text(url, transport, resolve_host):
    """Fetch text from a URL, following Location headers up to 5 hops.
    
    Args:
        url: The initial URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed (e.g., invalid scheme, port, or hostname).
    """
    max_hops = 5
    
    current_url = url
    hop_count = 0
    
    while hop_count <= max_hops:
        # Resolve the hostname
        hostname = urllib.parse urlparse(current_url).hostname
        if not hostname:
            raise ValueError("Invalid URL")
            
        ip_addresses = resolve_host(hostname)
        if not ip_addresses:
            raise ValueError("Hostname does not resolve to an IP address")
        
        # Check scheme and port
        parsed = urllib.parse urlparse(current_url)
        scheme = parsed.scheme.lower()
        port = parsed.port
        
        if scheme not in ['http', 'https']:
            raise ValueError("Only HTTP and HTTPS schemes are allowed")
        
        if scheme == 'http':
            if port != 80:
                raise ValueError("HTTP must use port 80")
        elif scheme == 'https':
            if port != 443:
                raise ValueError("HTTPS must use port 443")
        
        # Make the request
        try:
            response = transport(current_url)
            status, headers, body = response
            
            if status != 200:
                raise ValueError("Only 200 status codes are accepted")
            
            return body
            
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        # Follow Location header
        location = headers.get('Location')
        if location:
            current_url = location
            hop_count += 1
        else:
            break
    
    raise ValueError("Maximum hops exceeded")
