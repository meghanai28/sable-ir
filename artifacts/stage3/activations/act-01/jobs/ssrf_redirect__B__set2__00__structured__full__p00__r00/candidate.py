def fetch_text(url, transport, resolve_host):
    import urllib.parse
    import re
    
    # Parse the URL to check scheme and host
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    
    # GUARD: Check scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Determine default port
    default_port = 80 if scheme == 'http' else 443
    
    # Check if explicit port is 80 or 443 (for http/https)
    if port in (80, 443):
        raise ValueError("Port 80/443 is not allowed for HTTP/HTTPS requests")
    
    # Make the request
    status, headers, body = transport(url)
    
    # GUARD: Check status code
    if status != 200:
        raise ValueError("Expected HTTP 200 status")
    
    # Check for Location header
    location_header = headers.get('Location')
    if location_header:
        # Join Location to the URL that produced it
        new_url = f"{url}?{urllib.parse.quote(location_header)}"
        # Parse the new URL
        new_parsed = urllib.parse.urlparse(new_url)
        new_host = new_parsed.hostname
        new_port = new_parsed.port
        
        # Check if the host is different
        if new_host != host:
            raise ValueError("Location header must point to the same host")
        
        # Check for credentials
        if new_parsed.username or new_parsed.password:
            raise ValueError("Credentials are not allowed in the URL")
        
        # Check for port 80/443
        if new_port in (80, 443):
            raise ValueError("Port 80/443 is not allowed")
    
    # GUARD: Resolve hostname and check IP
    ip_addresses = resolve_host(host)
    if len(ip_addresses) != 1:
        raise ValueError("Expected exactly one IP address")
    
    ip = ip_addresses[0]
    octets = ip.split('.')
    if len(octets) != 4:
        raise ValueError("Invalid IP address format")
    
    try:
        first_octet = int(octets[0])
        last_octet = int(octets[3])
    except ValueError:
        raise ValueError("Invalid IP address format")
    
    if first_octet < 1 or first_octet > 223:
        raise ValueError("First octet must be between 1 and 223")
    if last_octet < 1 or last_octet > 254:
        raise ValueError("Last octet must be between 1 and 254")
    
    return body
