def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict host containment checks.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the request is disallowed (wrong scheme/port, no IPs, bad status).
    """
    from urllib.parse import urlparse, urljoin
    
    # Parse the initial URL
    initial_parsed = urlparse(url)
    
    # Define allowed schemes and ports
    allowed_schemes = {
        'http': 80,
        'https': 443
    }
    
    # Validate scheme and port
    scheme = initial_parsed.scheme.lower()
    port = initial_parsed.port
    if scheme not in allowed_schemes:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    allowed_port = allowed_schemes[scheme]
    if port is not None and port != allowed_port:
        raise ValueError(f"Port {port} not allowed for scheme {scheme}")
    
    # Resolve the initial hostname
    initial_host = initial_parsed.hostname
    if initial_host is None:
        raise ValueError("Invalid hostname in URL")
    
    ip_addresses = resolve_host(initial_host)
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for hostname: {initial_host}")
    
    # Build the canonical target host specification (scheme + port + host)
    # We will use the first resolved IP to determine the 'public address' for comparison
    canonical_host_info = (scheme, allowed_port, initial_host, ip_addresses[0])
    
    def is_same_host(parsed_url, current_ip):
        """Check if a URL has the same scheme, port, host, and DNS/IP as the target."""
        parsed = parsed_url
        
        # Check scheme
        if parsed.scheme.lower() != canonical_host_info[0]:
            return False
        
        # Check port (None means default, which is allowed)
        if parsed.port is not None:
            if parsed.port != canonical_host_info[1]:
                return False
        
        # Check host
        if parsed.hostname is None:
            return False
        if parsed.hostname != canonical_host_info[2]:
            return False
        
        # Check DNS/IP (must match the resolved IP of the target)
        if not ip_addresses:
            return False
        if current_ip not in ip_addresses:
            return False
            
        return True
    
    def is_same_host_no_ip_check(parsed_url):
        """Check if a URL has the same scheme, port, and host (ignoring IP resolution for now, assuming DNS matches host)."""
        parsed = parsed_url
        
        if parsed.scheme.lower() != canonical_host_info[0]:
            return False
        
        if parsed.port is not None:
            if parsed.port != canonical_host_info[1]:
                return False
        
        if parsed.hostname is None:
            return False
        if parsed.hostname != canonical_host_info[2]:
            return False
            
        return True
    
    # Current URL state
    current_url = url
    current_parsed = urlparse(url)
    current_location_count = 0
    max_hops = 5
    
    while current_location_count < max_hops:
        # Check if we have a Location header
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        # Check for Location header
        location = None
        for key, value in headers.items():
            if key.lower() == 'location':
                location = value
                break
        
        if location is None:
            # No Location header, but status is not 200 (or we just want to return body)
            # According to plan: "return the response body for status 200 and raise ValueError for every other status"
            # However, if there's no Location, we might just return the body or raise?
            # Plan says: "return the response body for status 200". If not 200, raise ValueError.
            raise ValueError(f"Unexpected status code: {status}")
        
        # Resolve the Location URL
        try:
            location_parsed = urlparse(location)
        except Exception:
            raise ValueError(f"Invalid Location URL: {location}")
        
        # Check containment before following
        if not is_same_host_no_ip_check(location_parsed):
            raise ValueError(f"Location URL outside target host: {location}")
        
        # Resolve the Location hostname
        location_host = location_parsed.hostname
        if location_host is None:
            raise ValueError(f"No hostname in Location URL: {location}")
        
        location_ips = resolve_host(location_host)
        if not location_ips:
            raise ValueError(f"No IP addresses found for Location hostname: {location_host}")
        
        # Check if the Location's resolved IP is within the target host's IPs
        # The plan says: "reject every Location whose resolved destination is outside the target host"
        # This implies we check if the Location's host matches the target host exactly.
        if location_host != canonical_host_info[2]:
            raise ValueError(f"Location hostname {location_host} does not match target host {canonical_host_info[2]}")
        
        # Check DNS/IP match (must have same DNS and public address)
        # "each Location must be resolved against the current URL and must have the same scheme, port, credentials, DNS, and public address as the initial destination"
        # DNS check: The resolved IPs must be the same as the initial destination's IPs
        if not all(ip in ip_addresses for ip in location_ips):
            raise ValueError(f"Location IP addresses {location_ips} do not match target IP addresses {ip_addresses}")
        
        # Build the new URL for the Location
        # We need to handle credentials and path correctly
        new_url = urljoin(current_url, location)
        
        # Parse the new URL to ensure it's valid and check for .. segments
        new_parsed = urlparse(new_url)
        
        # Check for .. segments in path or query
        # A simple check: if the path contains .., it might be dangerous
        # However, urljoin handles some of this, but we should be strict.
        # Let's check if the path contains ..
        if '..' in new_parsed.path or '..' in new_parsed.query:
            raise ValueError("Location URL contains .. segments")
        
        # Check if the new URL has the same host
        if new_parsed.hostname is None:
            raise ValueError("Invalid hostname in new URL")
        if new_parsed.hostname != canonical_host_info[2]:
            raise ValueError(f"New URL hostname {new_parsed.hostname} does not match target host {canonical_host_info[2]}")
        
        # Check port
        if new_parsed.port is not None:
            if new_parsed.port != canonical_host_info[1]:
                raise ValueError(f"New URL port {new_parsed.port} does not match target port {canonical_host_info[1]}")
        
        # Check scheme
        if new_parsed.scheme.lower() != canonical_host_info[0]:
            raise ValueError(f"New URL scheme {new_parsed.scheme} does not match target scheme {canonical_host_info[0]}")
        
        # Check credentials (if any)
        if new_parsed.username is not None or new_parsed.password is not None:
            raise ValueError("Credentials not allowed in new URL")
        
        # Update current URL
        current_url = new_url
        current_parsed = new_parsed
        current_location_count += 1
    
    # If we exit the loop (max hops reached) without returning, raise ValueError
    raise ValueError("Maximum number of Location hops reached")
