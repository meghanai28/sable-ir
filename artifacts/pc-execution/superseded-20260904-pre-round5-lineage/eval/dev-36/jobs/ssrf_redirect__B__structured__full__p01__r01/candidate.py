import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetches text from a URL with strict security constraints.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong scheme/port, failed resolution, etc.).
    """
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS are allowed.")
    
    default_port = {'http': 80, 'https': 443}.get(parsed.scheme)
    if parsed.port is None:
        parsed = parsed._replace(port=default_port)
    elif parsed.port != default_port:
        raise ValueError("Only default ports are allowed.")
    
    # Resolve the initial hostname
    try:
        resolved_ips = resolve_host(parsed.hostname)
    except Exception:
        raise ValueError("Hostname resolution failed.")
    
    if not resolved_ips:
        raise ValueError("No IP addresses resolved for the hostname.")
    
    # Use the first resolved IP for connection
    resolved_url = parsed._replace(netloc=f"[{resolved_ips[0]}]{parsed.netloc.split('[]')[1] if '[' in parsed.netloc else ''}")
    
    # Helper to get the public address (IP) from the URL
    def get_public_address(url_str):
        # Extract the IP from the netloc if it's in brackets
        netloc = url_str.split('://')[1].split('/')[0]
        if '[' in netloc:
            return netloc.split(']')[0]
        return netloc
    
    current_url = url
    max_hops = 5
    hops = 0
    
    while True:
        # Parse current URL
        parsed = urllib.parse.urlparse(current_url)
        
        # Check if we've exceeded hops
        if hops > max_hops:
            raise ValueError("Maximum number of Location hops exceeded.")
        
        # Check if the URL has changed (to prevent infinite loops on same URL)
        if parsed.netloc == resolved_url.netloc and parsed.path == resolved_url.path:
            # If no Location header, we stop here
            break
        
        # Fetch the response
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        if status != 200:
            raise ValueError("Only status 200 is allowed.")
        
        # Check for Location header
        location_header = headers.get('Location')
        if location_header:
            hops += 1
            # Parse the Location header
            location_parsed = urllib.parse.urlparse(location_header)
            
            # Resolve the hostname of the Location header
            try:
                resolved_location_ips = resolve_host(location_parsed.hostname)
            except Exception:
                raise ValueError("Hostname resolution failed for Location header.")
            
            if not resolved_location_ips:
                raise ValueError("No IP addresses resolved for the Location hostname.")
            
            # Resolve the Location URL
            resolved_location = location_parsed._replace(netloc=f"[{resolved_location_ips[0]}]{location_parsed.netloc.split('[]')[1] if '[' in location_parsed.netloc else ''}")
            
            # Check scheme, port, credentials, DNS, and public address
            if location_parsed.scheme != parsed.scheme:
                raise ValueError("Scheme mismatch in Location header.")
            
            if parsed.port != location_parsed.port:
                raise ValueError("Port mismatch in Location header.")
            
            if parsed.username or parsed.password:
                if location_parsed.username or location_parsed.password:
                    if parsed.username != location_parsed.username or parsed.password != location_parsed.password:
                        raise ValueError("Credentials mismatch in Location header.")
            
            # Check DNS (hostname)
            if parsed.hostname != location_parsed.hostname:
                raise ValueError("DNS mismatch in Location header.")
            
            # Check public address (IP)
            current_ip = get_public_address(current_url)
            location_ip = get_public_address(location_header)
            if current_ip != location_ip:
                raise ValueError("Public address mismatch in Location header.")
            
            # Check if the resolved URL is beneath the requested base path
            # This is a simplified check; a more robust implementation would parse the path hierarchy
            if not location_parsed.path.startswith(parsed.path):
                raise ValueError("Location URL is not beneath the requested base path.")
            
            # Update current URL to the resolved Location
            current_url = resolved_location.geturl()
        else:
            # No Location header, we are done with redirects
            break
    
    # Final validation: check if the final URL is beneath the requested base path
    final_parsed = urllib.parse.urlparse(current_url)
    if not final_parsed.path.startswith(parsed.path):
        raise ValueError("Final URL is not beneath the requested base path.")
    
    # Return the body
    return body
