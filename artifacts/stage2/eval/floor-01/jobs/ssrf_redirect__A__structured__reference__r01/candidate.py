def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation.
    
    Args:
        url: The URL to fetch from.
        transport: A function(url) -> (status, headers, body) that makes the request.
        resolve_host: A function(hostname) -> list of textual IP addresses.
    
    Returns:
        The response body as a string for a 200 status.
    
    Raises:
        ValueError: If the URL scheme/port/host is disallowed or if the resolved
                    address is not public, or if a redirect is encountered.
    """
    import urllib.parse
    
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    hostname = parsed.hostname
    
    # Validate scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    # Validate port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        if scheme == 'http' and port != 80:
            raise ValueError("Disallowed port for HTTP")
        if scheme == 'https' and port != 443:
            raise ValueError("Disallowed port for HTTPS")
    
    # Validate hostname presence
    if hostname is None:
        raise ValueError("Invalid URL")
    
    # Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
    except Exception:
        raise ValueError("Resolve host failed")
    
    if not resolved_ips:
        raise ValueError("No public addresses resolved")
    
    # Check if any resolved address is non-public (e.g., localhost, private)
    # Common non-public ranges: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, ::1, etc.
    def is_public_ip(ip):
        # IPv4 check
        if '.' in ip:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            try:
                octets = [int(p) for p in parts]
                # 10.0.0.0/8
                if octets[0] == 10:
                    return False
                # 172.16.0.0/12
                if octets[0] == 172 and 32 <= octets[1] <= 63:
                    return False
                # 192.168.0.0/16
                if octets[0] == 192 and octets[1] == 168:
                    return False
                # 127.0.0.0/8
                if octets[0] == 127:
                    return False
                # 0.0.0.0
                if octets[0] == 0:
                    return False
                # 224.0.0.0/4 (multicast)
                if octets[0] >= 224:
                    return False
                # 240.0.0.0/4 (reserved)
                if octets[0] >= 240:
                    return False
            except ValueError:
                return False
        # IPv6 check
        elif ip.startswith(('::', '::1', 'fe80:')):
            return False
        else:
            return True
    
    for ip in resolved_ips:
        if not is_public_ip(ip):
            raise ValueError("Non-public address resolved")
    
    # Make the request
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError("Non-200 status")
    
    return body.decode('utf-8') if isinstance(body, bytes) else body
