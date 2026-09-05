import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict scheme/port validation and redirect handling.
    
    Args:
        url: The target URL (untrusted input).
        transport: A function(url) -> (status, headers, body) tuple.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the scheme is not HTTP or HTTPS, or if validation fails.
    """
    # Parse the initial URL to extract components
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # Default ports: HTTP=80, HTTPS=443
    allowed_ports = {80: 80, 443: 443}
    
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    if port != allowed_ports.get(scheme):
        raise ValueError(f"Only default ports for {scheme} are allowed.")
    
    # Resolve the initial hostname
    initial_host = parsed_url.hostname
    if not initial_host:
        raise ValueError("Invalid URL: missing hostname.")
    
    try_ips = resolve_host(initial_host)
    if not try_ips:
        raise ValueError(f"Could not resolve hostname: {initial_host}")
    
    # Build the initial request URL with scheme and port
    request_url = f"{scheme}://{initial_host}:{port}{parsed_url.path}"
    
    # Function to validate and resolve a URL component
    def validate_and_resolve_url(current_url: str, max_hops: int = 5) -> str:
        """
        Validate scheme, port, and resolve hostname.
        Returns the resolved URL string or raises ValueError.
        """
        # Check scheme
        if not current_url.startswith(('http://', 'https://')):
            raise ValueError("Invalid scheme in redirect.")
        
        # Parse the redirect URL
        redirect_parsed = urllib.parse.urlparse(current_url)
        redirect_scheme = redirect_parsed.scheme.lower()
        redirect_port = redirect_parsed.port
        
        # Validate port
        if redirect_port is None:
            redirect_port = 80 if redirect_scheme == 'http' else 443
        
        if redirect_port != allowed_ports.get(redirect_scheme):
            raise ValueError(f"Invalid port in redirect URL.")
        
        # Extract hostname
        redirect_host = redirect_parsed.hostname
        if not redirect_host:
            raise ValueError("Invalid hostname in redirect URL.")
        
        # Resolve hostname
        resolved_ips = resolve_host(redirect_host)
        if not resolved_ips:
            raise ValueError(f"Could not resolve hostname in redirect: {redirect_host}")
        
        # Construct the new URL string
        new_url = f"{redirect_scheme}://{redirect_host}:{redirect_port}{redirect_parsed.path}"
        
        # Check redirect limit
        if max_hops > 0:
            return validate_and_resolve_url(new_url, max_hops - 1)
        else:
            return new_url
    
    # Perform redirect resolution
    final_url = validate_and_resolve_url(request_url)
    
    # Create the request
    try:
        req = urllib.request.Request(final_url)
        response = urllib.request.urlopen(req)
        
        # Check status code
        status_code = response.status
        if status_code != 200:
            raise ValueError(f"Unexpected status code: {status_code}")
        
        # Read body
        body = response.read().decode('utf-8')
        return body
    
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP error occurred: {e.code} {e.reason}")
    except Exception as e:
        raise ValueError(f"Network error: {str(e)}")
