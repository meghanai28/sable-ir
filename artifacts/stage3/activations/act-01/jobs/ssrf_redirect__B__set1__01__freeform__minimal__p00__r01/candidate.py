def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url (str): The URL to fetch from.
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of IP addresses.
    
    Returns:
        str: The response body for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, host resolution fails,
                    redirect exceeds limits, or status is not 200.
    """
    import urllib.parse
    import socket
    import re
    
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve the host
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed.")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for the host.")
    
    # Validate that at least one valid IP exists (basic check)
    if not any(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) for ip in ip_addresses):
        # If the resolver returns non-IP strings, treat as failure or strict validation
        # The spec says "raise ValueError if resolution fails", implying we need valid IPs
        # Assuming resolve_host returns valid IPs or raises; if it returns garbage, we fail
        pass  # Proceed if IPs are valid, otherwise the check below will catch it if we want strictness
    # Actually, let's be strict: if resolve_host returns something that isn't a valid IP, it's a failure
    if not ip_addresses or not all(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) for ip in ip_addresses):
        raise ValueError("Invalid IP addresses returned from resolve_host.")
    
    # Determine the base scheme, port, credentials, and DNS name
    base_scheme = parsed_url.scheme
    base_port = parsed_url.port
    base_credentials = parsed_url.username + ":" + parsed_url.password
    base_dns = parsed_url.hostname
    base_ip = None
    # Determine the public address (first resolved IP)
    base_ip = ip_addresses[0]
    
    # Track hops
    current_url = url
    hops = 0
    max_hops = 5
    
    while hops <= max_hops:
        # Make the request
        status, headers, body = transport(current_url)
        
        # Check status code
        if status != 200:
            raise ValueError("Response status code is not 200.")
        
        # Check for Location header (redirect)
        location = None
        if 'Location' in headers:
            location = headers['Location']
        
        if location:
            hops += 1
            if hops > max_hops:
                raise ValueError("Redirect exceeded maximum hop limit.")
            
            # Parse the Location header
            try:
                location_parsed = urllib.parse.urlparse(location)
            except Exception:
                raise ValueError("Invalid Location header format.")
            
            # Validate the Location header against the current URL
            # Must share the same scheme, port, credentials, DNS name, and public address
            if location_parsed.scheme.lower() != base_scheme:
                raise ValueError("Redirect scheme mismatch.")
            if location_parsed.port != base_port:
                raise ValueError("Redirect port mismatch.")
            if location_parsed.username != base_credentials.split(':')[0] or (':' in base_credentials and location_parsed.password != base_credentials.split(':')[1]):
                # Simplified credential check: if credentials exist in base, they must match
                if base_credentials:
                    if location_parsed.username != base_credentials.split(':')[0] or location_parsed.password != base_credentials.split(':')[1]:
                        raise ValueError("Redirect credentials mismatch.")
                else:
                    # If no credentials in base, ensure none in location
                    if location_parsed.username or location_parsed.password:
                        raise ValueError("Redirect introduced credentials.")
            if location_parsed.hostname != base_dns:
                raise ValueError("Redirect DNS name mismatch.")
            if location_parsed.hostname and not all(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) for ip in ip_addresses):
                # If the resolved IPs don't match the hostname, it's an issue
                pass
            
            # Check if the resolved IP matches the public address
            # We need to resolve the new hostname to check IP
            new_hostname = location_parsed.hostname
            if new_hostname:
                try:
                    new_ip_addresses = resolve_host(new_hostname)
                except Exception:
                    raise ValueError("Host resolution failed for redirect target.")
                
                if not new_ip_addresses:
                    raise ValueError("No IP addresses resolved for redirect target.")
                
                if not all(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) for ip in new_ip_addresses):
                    raise ValueError("Invalid IP addresses for redirect target.")
                
                # Check if the public address (first IP) matches
                if new_ip_addresses[0] != base_ip:
                    raise ValueError("Redirect IP mismatch.")
            
            current_url = location
        else:
            # No redirect, break the loop
            break
    
    # Return the body
    return body
