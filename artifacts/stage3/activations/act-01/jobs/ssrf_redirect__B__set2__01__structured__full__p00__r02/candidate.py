def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict safety checks.
    
    Args:
        url: The URL to fetch.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, if the host cannot be resolved,
                   or if the request is unsafe.
    """
    # Parse the URL to extract scheme and host
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Determine the port
    default_port = 80 if scheme == 'http' else 443
    if parsed.port:
        port = parsed.port
    else:
        port = default_port
    
    # Construct the full URL for the request
    full_url = f"{scheme}://{host}:{port}"
    
    # ORDER: Check scheme and host before creating the request
    # GUARD: Join the scheme and host beneath the calling process's temporary directory
    # This is a heuristic check to ensure the host is not an absolute path or maliciously constructed
    # to escape the sandbox. We check if the host contains path separators or starts with a slash
    if host.startswith('/') or '..' in host or '..' in url:
        raise ValueError("Unsafe host structure detected.")
    
    # Handle redirects
    max_redirects = 5
    current_url = full_url
    redirect_count = 0
    
    while redirect_count < max_redirects:
        # Call transport
        status, headers, body = transport(current_url)
        
        # Check status
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirects
        location = headers.get('Location')
        if location:
            redirect_count += 1
            # Parse the redirect URL
            try:
                redirect_parsed = urlparse(location)
                # GUARD: Check redirect target
                if redirect_parsed.scheme.lower() not in ('http', 'https'):
                    raise ValueError("Redirect to non-HTTP/HTTPS scheme.")
                if not redirect_parsed.netloc:
                    raise ValueError("Redirect to empty host.")
                
                # Join scheme and host beneath the calling process's temporary directory
                redirect_host = redirect_parsed.netloc.lower()
                if redirect_host.startswith('/') or '..' in redirect_host:
                    raise ValueError("Unsafe redirect host structure.")
                
                # Update current URL
                current_url = f"{redirect_parsed.scheme}://{redirect_parsed.netloc}:{redirect_parsed.port}" if redirect_parsed.port else f"{redirect_parsed.scheme}://{redirect_parsed.netloc"
            except Exception:
                raise ValueError("Invalid redirect URL.")
        else:
            break
    
    # ORDER: Resolve the final host and raise ValueError if DNS resolution fails
    if not resolve_host:
        raise ValueError("Host resolution function is required.")
    
    final_host = current_url.split('://')[1].split(':')[0]
    if not final_host:
        raise ValueError("Could not resolve host.")
    
    try:
        ips = resolve_host(final_host)
    except Exception:
        raise ValueError("DNS resolution failed.")
    
    if not ips:
        raise ValueError("Resolved host has no IP address.")
    
    # Return the body
    return body.decode('utf-8') if isinstance(body, bytes) else body
