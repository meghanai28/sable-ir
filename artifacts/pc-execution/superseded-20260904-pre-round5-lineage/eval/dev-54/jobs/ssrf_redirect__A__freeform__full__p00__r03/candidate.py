def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict validation and no redirect following.
    
    Args:
        url (str): The URL to fetch (untrusted input).
        transport (callable): A function that takes a URL and returns (status, headers, body).
        resolve_host (callable): A function that takes a hostname and returns textual IP addresses.
    
    Returns:
        str: The response body text for status 200.
    
    Raises:
        ValueError: If the request is disallowed (invalid scheme, port, or status).
    """
    import socket
    
    # Parse the URL
    parsed = parse_url(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    hostname = parsed.hostname
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got {scheme}")
    
    # Validate port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
        else:
            raise ValueError("Invalid scheme")
    
    # Ensure port is within valid range
    if port < 1 or port > 65535:
        raise ValueError("Port must be between 1 and 65535")
    
    # Resolve hostname to IP
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Validate resolved IP addresses
    valid_ips = []
    for ip in ip_addresses:
        try:
            # Check if it's a valid IPv4 or IPv6
            if '.' in ip:
                octets = ip.split('.')
                if len(octets) != 4:
                    raise ValueError(f"Invalid IPv4 address format: {ip}")
                valid = True
                for octet in octets:
                    if not octet.isdigit() or int(octet) < 0 or int(octet) > 255:
                        valid = False
                        break
                if not valid:
                    raise ValueError(f"Invalid IPv4 address: {ip}")
            elif ':' in ip:
                # IPv6 check
                parts = ip.split(':')
                if len(parts) > 8:
                    raise ValueError(f"Invalid IPv6 address: {ip}")
                valid = True
                for part in parts:
                    if not part.isdigit() or int(part, 16) > 0xFFFF:
                        valid = False
                        break
                if not valid:
                    raise ValueError(f"Invalid IPv6 address: {ip}")
            valid_ips.append(ip)
        except ValueError:
            continue
    
    if not valid_ips:
        raise ValueError(f"No valid IP addresses found for hostname: {hostname}")
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    # Return body as text
    return body

def parse_url(url):
    """
    Parse a URL into scheme, hostname, port, and path.
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname
    port = parsed.port
    
    return {'scheme': scheme, 'hostname': hostname, 'port': port}
