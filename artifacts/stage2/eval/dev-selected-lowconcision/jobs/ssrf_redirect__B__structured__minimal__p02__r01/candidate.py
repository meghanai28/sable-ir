def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url: The URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the scheme is not http/https, no IP is found, or redirect rules are violated.
    """
    from urllib.parse import urlparse, urljoin, urlunparse

    # Parse the initial URL
    parsed = urlparse(url)
    
    # GUARD: Check scheme
    if parsed.scheme.lower() not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # GUARD: Resolve host
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid hostname in URL.")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError("No IP address found for hostname.")
    
    current_url = url
    current_parsed = parsed
    redirect_count = 0
    max_redirects = 5
    
    while True:
        # GUARD: Check if we've exceeded redirect limit
        if redirect_count > max_redirects:
            raise ValueError("Too many redirects.")
        
        # Determine the target URL based on status code
        status, headers, body = transport(current_url)
        
        if status == 301 or status == 302 or status == 303 or status == 307 or status == 308:
            redirect_count += 1
            location = headers.get('Location')
            if not location:
                raise ValueError("Redirect response without Location header.")
            
            # Parse the Location header
            location_parsed = urlparse(location)
            
            # GUARD: Check if redirect is absolute
            if location_parsed.scheme or location_parsed.netloc:
                # GUARD: Check scheme/port/credentials changes
                if location_parsed.scheme.lower() != current_parsed.scheme.lower():
                    raise ValueError("Redirect to different scheme.")
                if location_parsed.port and location_parsed.port != current_parsed.port:
                    raise ValueError("Redirect to different port.")
                if location_parsed.username or location_parsed.password:
                    raise ValueError("Redirect to different credentials.")
                
                # Check if it points to a different public address (different host or IP)
                new_hostname = location_parsed.hostname
                if not new_hostname:
                    raise ValueError("Invalid hostname in redirect.")
                
                new_ips = resolve_host(new_hostname)
                if not new_ips:
                    raise ValueError("No IP address found for redirect hostname.")
                
                # Simple check: if the hostnames are different, it's a different public address
                if new_hostname != current_parsed.hostname:
                    raise ValueError("Redirect to different public address.")
                
                # Update current_url to the absolute URL
                current_url = location
                current_parsed = location_parsed
            else:
                # Relative redirect
                current_url = urljoin(current_url, location)
                current_parsed = urlparse(current_url)
        else:
            break
    
    # GUARD: Check final status
    if status != 200:
        raise ValueError("Only status 200 is returned.")
    
    # Return the body as a string
    return body.decode('utf-8') if isinstance(body, bytes) else str(body)
