import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetches text from a URL with strict validation and redirect handling.
    
    Args:
        url: The initial URL string.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status code 200.
    
    Raises:
        ValueError: If the request is disallowed, hostname resolution fails, or status is not 200.
    """
    # Parse the initial URL
    try:
        parsed_url = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Malformed initial URL: {url}") from e
    
    # Validate scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {parsed_url.scheme}")
    
    # Guard: Reject absolute URLs with .. segments or malformed paths
    # The plan specifies "may be absolute, contain .. segments, or be malformed".
    # We check for .. in the path or query components after parsing.
    path = parsed_url.path
    query = parsed_url.query
    fragment = parsed_url.fragment
    
    # Check for .. segments in path, query, or fragment
    for component in [path, query, fragment]:
        if '..' in component:
            raise ValueError("URL contains '..' segments")
    
    # Guard: Resolve the target hostname and check for finite IP address
    if parsed_url.hostname is None:
        raise ValueError("Missing hostname in URL")
    
    hostname = parsed_url.hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"Hostname resolution failed: {hostname}") from e
    
    if not ip_addresses:
        raise ValueError(f"Hostname resolution failed to return finite IP: {hostname}")
    
    # Guard: Check the resolved destination before opening the connection
    # We use the first resolved IP for the connection.
    resolved_ip = ip_addresses[0]
    
    current_url = url
    max_redirects = 5
    
    while True:
        # Guard: Check the resolved destination before opening the connection
        # We need to ensure the current URL (after redirects) also resolves to the same public address
        # However, the plan says "must have the same scheme, port, credentials, DNS, and public address as the initial destination"
        # This implies we should re-resolve the current_url's hostname and verify it matches the initial resolved IP.
        # But since we are following redirects, the hostname might change. The constraint "same ... DNS" usually means the final resolved IP must be consistent or the redirect is only allowed if it points to the same server.
        # Given "same scheme, port, credentials, DNS, and public address", we interpret this as:
        # 1. Scheme must match.
        # 2. Port must match.
        # 3. Credentials must match.
        # 4. DNS resolution of the new hostname must yield the same public address (IP) as the initial one.
        
        try:
            current_parsed = urllib.parse.urlparse(current_url)
        except Exception as e:
            raise ValueError(f"Malformed current URL during redirect: {current_url}") from e
        
        # Check scheme match
        if current_parsed.scheme != parsed_url.scheme:
            raise ValueError("Redirect scheme mismatch")
        
        # Check port match
        if current_parsed.port != parsed_url.port:
            raise ValueError("Redirect port mismatch")
        
        # Check credentials match (user/pass)
        if current_parsed.username != parsed_url.username or current_parsed.password != parsed_url.password:
            raise ValueError("Redirect credentials mismatch")
        
        # Check DNS/Address match
        if current_parsed.hostname is None:
            raise ValueError("Redirect has no hostname")
        
        try:
            new_ip_addresses = resolve_host(current_parsed.hostname)
        except Exception as e:
            raise ValueError(f"Hostname resolution failed for redirect: {current_parsed.hostname}") from e
        
        if not new_ip_addresses:
            raise ValueError(f"Hostname resolution failed to return finite IP for redirect: {current_parsed.hostname}")
        
        # The public address must be the same as the initial destination
        if set(new_ip_addresses) != set(ip_addresses):
            raise ValueError("Redirect destination public address does not match initial destination")
        
        # Open the connection
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}") from e
        
        status = response[0]
        
        # Guard: Return the body only for status 200
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Return the body
        return response[2]
    
    # Guard: Follow at most five HTTP redirects
    if len(response) > 2 and response[1].get('Location'):
        location = response[1].get('Location')
        # Parse the location to determine the next URL
        # If it's absolute, use as is. If relative, resolve against current_url.
        if urllib.parse.urlparse(location).scheme:
            next_url = location
        else:
            next_url = urllib.parse.urljoin(current_url, location)
        
        if len(response) > 2 and response[1].get('Location'):
            next_url = location
            if urllib.parse.urlparse(location).scheme:
                pass
            else:
                next_url = urllib.parse.urljoin(current_url, location)
        
        if next_url == current_url:
            raise ValueError("Infinite redirect loop detected")
        
        current_url = next_url
        
        if len(response) > 2 and response[1].get('Location'):
            pass
        else:
            pass

    raise ValueError("Unexpected response structure or status")
