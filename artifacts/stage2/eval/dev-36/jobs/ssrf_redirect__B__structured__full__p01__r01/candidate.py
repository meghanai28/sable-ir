import socket
from urllib.parse import urlparse, urljoin

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL, validating scheme, resolving hostnames,
    following redirects, and returning the body for a 200 status.
    """
    parsed_url = urlparse(url)
    
    # GUARD: Check scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # GUARD: Resolve initial hostname
    try:
        ip_addresses = resolve_host(parsed_url.hostname)
    except ValueError:
        raise ValueError("Unable to resolve hostname")
    
    if not ip_addresses:
        raise ValueError("No IP addresses found for hostname")
    
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    while True:
        # Use the resolved IP for the request
        ip = ip_addresses[0]
        request_url = f"{parsed_url.scheme}://{ip}{parsed_url.path}"
        
        # Call transport to get response
        status, headers, body = transport(request_url)
        
        # GUARD: Check for disallowed status codes (though spec only explicitly mentions 200 return)
        # Assuming non-200 might be treated as error or we just don't return body
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError("Too many redirects")
            
            # Parse redirect location
            redirect_parsed = urlparse(location)
            current_parsed = urlparse(current_url)
            
            # GUARD: Check redirect constraints
            # 1. Same scheme but different port
            if redirect_parsed.scheme == current_parsed.scheme:
                if current_parsed.port != redirect_parsed.port:
                    raise ValueError("Redirect to different port")
            
            # 2. Missing credentials
            if not redirect_parsed.username or not redirect_parsed.password:
                raise ValueError("Redirect missing credentials")
            
            # 3. Non-public DNS entry (assume resolve_host handles this via ValueError)
            try:
                redirect_ip_addresses = resolve_host(redirect_parsed.hostname)
            except ValueError:
                raise ValueError("Redirect points to non-public DNS entry")
            
            if not redirect_ip_addresses:
                raise ValueError("Redirect points to non-public DNS entry")
            
            # Join URL and resolve again
            new_url = urljoin(current_url, location)
            # Re-parse to ensure we have the right scheme and port
            current_url = new_url
            current_parsed = urlparse(current_url)
            # Update current_ip_addresses to the new host's IPs
            ip_addresses = resolve_host(redirect_parsed.hostname)
        else:
            break
    
    return body
