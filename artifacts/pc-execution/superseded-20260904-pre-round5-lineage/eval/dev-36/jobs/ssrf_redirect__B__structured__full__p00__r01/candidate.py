import urllib.request
import urllib.parse
import urllib.error
import socket
import ssl
import sys

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and redirect handling.
    
    Args:
        url (str): The initial URL to fetch.
        transport (callable): A function that returns (status, headers, body) for a given URL.
        resolve_host (callable): A function that resolves a hostname to IP addresses.
    
    Returns:
        str: The response body for a 200 status code.
    
    Raises:
        ValueError: If the request is disallowed, status is not 200, or resolution fails.
    """
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme and port
    valid_schemes = {'http', 'https'}
    if parsed.scheme.lower() not in valid_schemes:
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed. Got: {parsed.scheme}")
    
    # Determine default port
    default_port = {'http': 80, 'https': 443}.get(parsed.scheme.lower())
    if parsed.port is None:
        parsed = parsed._replace(port=default_port)
    
    # Resolve hostname
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid URL: missing hostname")
    
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not resolved_ips:
        raise ValueError(f"No IP addresses resolved for: {hostname}")
    
    # Function to validate and resolve a URL for redirects
    def validate_and_resolve_location(location):
        # Parse the location
        loc_parsed = urllib.parse.urlparse(location)
        
        # Check scheme
        if loc_parsed.scheme.lower() not in valid_schemes:
            raise ValueError(f"Redirect to invalid scheme: {loc_parsed.scheme}")
        
        # Check port
        if loc_parsed.port is None:
            loc_parsed = loc_parsed._replace(port=default_port)
        
        # Check credentials
        if parsed.username is not None or parsed.password is not None:
            if loc_parsed.username is None or loc_parsed.password is None:
                raise ValueError("Credentials mismatch in redirect")
        
        # Check DNS/public-address (scheme, port, hostname)
        if parsed.scheme.lower() != loc_parsed.scheme.lower():
            raise ValueError(f"Scheme mismatch in redirect: {parsed.scheme} vs {loc_parsed.scheme}")
        
        if parsed.port != loc_parsed.port:
            raise ValueError(f"Port mismatch in redirect: {parsed.port} vs {loc_parsed.port}")
        
        if parsed.hostname is not None and parsed.hostname.lower() != loc_parsed.hostname.lower():
            raise ValueError(f"Host mismatch in redirect: {parsed.hostname} vs {loc_parsed.hostname}")
        
        # Resolve the new hostname
        new_hostname = loc_parsed.hostname
        if new_hostname is None:
            raise ValueError("Invalid hostname in redirect")
        
        try:
            new_resolved = resolve_host(new_hostname)
        except Exception:
            raise ValueError(f"Failed to resolve hostname in redirect: {new_hostname}")
        
        if not new_resolved:
            raise ValueError(f"No IP addresses resolved for: {new_hostname}")
        
        return loc_parsed
    
    # Handle redirects
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    while redirect_count < max_redirects:
        # Validate final destination before opening connection
        try:
            validated_url = validate_and_resolve_location(current_url)
        except ValueError as e:
            raise ValueError(f"Redirect validation failed: {e}")
        
        # Call transport
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        # Check status code
        if status != 200:
            raise ValueError(f"Status code is not 200: {status}")
        
        # Return body
        return body.decode('utf-8') if isinstance(body, bytes) else body
        
        # Handle redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            current_url = location
        else:
            break
    
    raise ValueError("Maximum redirects reached or no redirect header")
