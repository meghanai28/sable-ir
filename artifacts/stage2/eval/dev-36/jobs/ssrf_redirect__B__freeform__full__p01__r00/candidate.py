import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict safety checks.
    
    Args:
        url: The initial URL to fetch from.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, if DNS lookup fails,
                   if the resolved IP is not public, or if status is not 200.
    """
    
    def is_public_ip(ip_str: str) -> bool:
        """
        Check if an IP address is public (not starting with 127.0.0.1, ::1, etc.).
        This is a simplified check based on the requirement to "raise ValueError if ... points to a public address".
        The plan implies we should only allow public addresses.
        """
        ip = ip_str.lower()
        # Private ranges
        if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.16.') or ip.startswith('172.17.') or ip.startswith('172.18.') or ip.startswith('172.19.') or ip.startswith('172.20.') or ip.startswith('172.21.') or ip.startswith('172.22.') or ip.startswith('172.23.') or ip.startswith('172.24.') or ip.startswith('172.25.') or ip.startswith('172.26.') or ip.startswith('172.27.') or ip.startswith('172.28.') or ip.startswith('172.29.') or ip.startswith('172.30.') or ip.startswith('172.31.') or ip.startswith('169.254.') or ip.startswith('0.'):
            return False
        if ip.startswith('::1') or ip.startswith('fc'):
            return False
        return True

    def parse_location(location: str, base_url: str) -> str:
        """
        Resolve a Location header against the current URL.
        Handles absolute and relative URLs.
        """
        parsed_base = urllib.parse.urlparse(base_url)
        
        # If absolute, use as-is
        if location.startswith(('http://', 'https://')):
            return location
        
        # If relative, resolve against base
        parsed_location = urllib.parse.urlparse(location)
        
        if parsed_location.scheme:
            # Should be handled by absolute check, but if it has a scheme, use it
            return location
        
        # Construct absolute URL
        if parsed_base.path:
            path = parsed_base.path.rstrip('/')
            if parsed_location.path:
                path = path + '/' + parsed_location.path.lstrip('/')
            else:
                path = parsed_base.path.rstrip('/')
        else:
            path = parsed_location.path.lstrip('/')
        
        query = parsed_location.query
        if query and parsed_base.query:
            query = parsed_base.query + '&' + query
        elif query:
            query = '?' + query
        
        fragment = parsed_location.fragment
        
        final_url = f"{parsed_base.scheme}://{parsed_base.netloc}{path}?{query}"
        if fragment:
            final_url += "#" + fragment
        
        return final_url

    # Parse initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Check scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Resolve hostname
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")
    
    try:
        ip_addresses = resolve_host(hostname)
    except Exception as e:
        raise ValueError(f"DNS lookup failed: {e}")
    
    if not ip_addresses:
        raise ValueError("No IP address found for hostname.")
    
    # Check if any public IP is found (assuming at least one public IP is needed)
    # The plan says "raise ValueError if resolve_host(hostname) returns no IP address"
    # and "raise ValueError ... unless ... its DNS lookup succeeds and points to a public address".
    # This implies we need at least one public IP.
    has_public_ip = False
    for ip in ip_addresses:
        if is_public_ip(ip):
            has_public_ip = True
            break
    
    if not has_public_ip:
        raise ValueError("No public IP address found for hostname.")
    
    # Use the first public IP for the connection
    public_ip = None
    for ip in ip_addresses:
        if is_public_ip(ip):
            public_ip = ip
            break
    
    if not public_ip:
        raise ValueError("No public IP address found for hostname.")
    
    current_url = url
    
    # Follow redirects (at most 5)
    for _ in range(5):
        status, headers, body = transport(current_url)
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        return body
        
        # If we get here, status is not 200, so we raise.
        # But we need to check for Location header for redirects.
        # The logic above returns early if 200.
        # If not 200, we should check for Location header.
        # However, the plan says "return the response body only when status is exactly 200".
        # So if status is not 200, we don't return. We check for redirects.
        
        # Re-evaluating the loop:
        # 1. Fetch.
        # 2. If 200, return body.
        # 3. If not 200, check for Location header.
        # 4. If Location header exists, parse it, check scheme/port/IP, then set current_url and repeat.
        # 5. If no Location header or redirect fails, raise ValueError.
        
        # Let's restructure the loop.
        pass
    
    # Restructured loop for redirect following
    current_url = url
    
    for _ in range(5):
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Check for Location header
        location_header = headers.get('Location')
        
        if not location_header:
            raise ValueError("No Location header found to follow redirect.")
        
        # Parse and validate Location
        location_url = parse_location(location_header, current_url)
        
        # Check scheme
        parsed_loc = urllib.parse.urlparse(location_url)
        if parsed_loc.scheme not in ('http', 'https'):
            raise ValueError("Redirect URL must have http or https scheme.")
        
        # Check port
        if parsed_loc.port != parsed_url.port:
            raise ValueError("Redirect URL must have the same port as the current URL.")
        
        # Check DNS
        loc_hostname = parsed_loc.hostname
        if not loc_hostname:
            raise ValueError("Invalid redirect URL: missing hostname.")
        
        try:
            loc_ips = resolve_host(loc_hostname)
        except Exception as e:
            raise ValueError(f"DNS lookup failed for redirect hostname: {e}")
        
        if not loc_ips:
            raise ValueError("No IP address found for redirect hostname.")
        
        # Check if public
        has_public_ip_loc = False
        for ip in loc_ips:
            if is_public_ip(ip):
                has_public_ip_loc = True
                break
        
        if not has_public_ip_loc:
            raise ValueError("No public IP address found for redirect hostname.")
        
        current_url = location_url
    
    raise ValueError("Too many redirects.")
