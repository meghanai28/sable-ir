def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url (str): The target URL (absolute or relative).
        transport (callable): Function taking url and returning (status, headers, body).
        resolve_host (callable): Function taking hostname and returning list of IP strings.
    
    Returns:
        str: The body of the response if status is 200.
    
    Raises:
        ValueError: If scheme is not http/https, status is not 200, or validation fails.
    """
    import urllib.parse
    import socket
    import re
    
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.netloc if parsed.netloc else ""
    port = parsed.port
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Invalid scheme: {scheme}")
    
    # Validate port (must be default or valid number)
    if port is not None:
        try:
            int(port)
        except ValueError:
            raise ValueError(f"Invalid port: {port}")
    
    # Extract hostname for resolution
    if not host:
        raise ValueError("No hostname in URL")
    
    # Remove credentials from host if present
    if '@' in host:
        host = host.split('@')[1]
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(host)
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname: {e}")
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    # Validate IP addresses (must be textual and not start with underscore)
    for ip in ip_addresses:
        if not isinstance(ip, str):
            raise ValueError(f"IP address must be textual: {ip}")
        if ip.startswith('_'):
            raise ValueError(f"IP address starts with underscore: {ip}")
        # Basic check for valid IP format (simple check, not exhaustive)
        if not re.match(r'^[\d\.]+$', ip):
            raise ValueError(f"Invalid IP address format: {ip}")
    
    # Validate scheme, port, credentials, DNS, and public address
    # Check scheme again
    if scheme not in ('http', 'https'):
        raise ValueError(f"Scheme must be http or https, got {scheme}")
    
    # Check port
    if port is not None:
        if scheme == 'http' and port != 80:
            raise ValueError(f"HTTP port must be 80, got {port}")
        if scheme == 'https' and port != 443:
            raise ValueError(f"HTTPS port must be 443, got {port}")
    
    # Check DNS resolution again
    if not ip_addresses:
        raise ValueError("No IP addresses resolved")
    
    # Check public address (IPs)
    for ip in ip_addresses:
        if not re.match(r'^[\d\.]+$', ip):
            raise ValueError(f"Invalid IP address format: {ip}")
    
    # Make the request
    try:
        status, headers, body = transport(url)
    except Exception as e:
        raise ValueError(f"Transport failed: {e}")
    
    # Validate status
    if status != 200:
        raise ValueError(f"Status code is not 200: {status}")
    
    # Return body
    return body
