import socket
import urllib.parse
import urllib.request
import urllib.error
import urllib.parse

def resolve_host(hostname):
    """
    Resolves a hostname to a list of IP addresses.
    This is a placeholder implementation as the actual resolution logic
    is expected to be provided by the environment or the specific
    `resolve_host` function called by the main function.
    In a real scenario, this would use socket.getaddrinfo.
    """
    try:
        info = socket.getaddrinfo(hostname, None)
        return [ip[4][0] for ip in info]
    except socket.gaierror:
        return []

def fetch_text(url, transport, resolve_host):
    """
    Fetches text from a URL.
    
    Args:
        url: The URL to fetch from (can be absolute or relative).
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        str: The body of the response for a 200 status code.
    
    Raises:
        ValueError: If the request is disallowed (bad scheme, port, or unresolved hostname).
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Check scheme and port
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Validate port
    if port != 80 and scheme == 'http':
        raise ValueError(f"Invalid port {port} for scheme {scheme}")
    if port != 443 and scheme == 'https':
        raise ValueError(f"Invalid port {port} for scheme {scheme}")
    
    # Resolve initial hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("No hostname in URL")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Build the base URL for following redirects
    base_url = parsed_url._replace(netloc=hostname).geturl()
    
    # Follow redirects (Location headers) at most 5 hops
    max_hops = 5
    current_url = base_url
    hops = 0
    
    while hops < max_hops:
        # Resolve hostname for the current URL
        current_parsed = urllib.parse.urlparse(current_url)
        current_hostname = current_parsed.hostname
        
        if not current_hostname:
            raise ValueError(f"Could not resolve hostname in current URL: {current_url}")
        
        current_ip_addresses = resolve_host(current_hostname)
        if not current_ip_addresses:
            raise ValueError(f"Could not resolve hostname: {current_hostname}")
        
        # Check scheme and port for the current URL
        current_scheme = current_parsed.scheme.lower()
        current_port = current_parsed.port
        
        if current_scheme != scheme:
            raise ValueError(f"Redirected to disallowed scheme: {current_scheme}")
        
        if current_port != 80 and current_scheme == 'http':
            raise ValueError(f"Redirected to invalid port {current_port} for scheme {current_scheme}")
        if current_port != 443 and current_scheme == 'https':
            raise ValueError(f"Redirected to invalid port {current_port} for scheme {current_scheme}")
        
        # Make the request
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        status_code = response[0]
        headers = response[1]
        body = response[2]
        
        if status_code == 200:
            return body
        
        # Check for Location header
        location_header = headers.get('location')
        if not location_header:
            # No location header, but not 200, so we stop (or could raise)
            # The spec says "return the body for status 200", implying we stop if not 200
            # However, if it's not 200 and no location, we just stop.
            # But if it's not 200, we shouldn't return body.
            pass
        else:
            # Parse the Location header
            # The Location header might be absolute or relative
            if location_header.startswith(('http://', 'https://')):
                redirect_url = location_header
            else:
                # Relative URL, resolve against current URL
                redirect_url = urllib.parse.urljoin(current_url, location_header)
            
            # Increment hop count
            hops += 1
            
            # Parse the redirect URL
            redirect_parsed = urllib.parse.urlparse(redirect_url)
            
            # Re-validate scheme and port for the redirect URL
            redirect_scheme = redirect_parsed.scheme.lower()
            redirect_port = redirect_parsed.port
            
            if redirect_scheme != scheme:
                raise ValueError(f"Redirected to disallowed scheme: {redirect_scheme}")
            
            if redirect_port != 80 and redirect_scheme == 'http':
                raise ValueError(f"Redirected to invalid port {redirect_port} for scheme {redirect_scheme}")
            if redirect_port != 443 and redirect_scheme == 'https':
                raise ValueError(f"Redirected to invalid port {redirect_port} for scheme {redirect_scheme}")
            
            # Update current_url for the next iteration
            current_url = redirect_url
    
    # If we exit the loop without returning, it means we hit max hops or no 200
    # We should raise an error or return None. The spec implies we should only return body for 200.
    # If we get here, it's an error condition (max hops reached or non-200 status).
    raise ValueError("Maximum redirect hops reached or non-200 status code")
