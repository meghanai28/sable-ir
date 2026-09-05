import socket
import urllib.parse
import urllib.request
import urllib.error

def resolve_host(hostname):
    """Resolve hostname to list of textual IP addresses."""
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [addr[4][0] for addr in ip_addresses]
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from URL using provided transport.
    
    Args:
        url: The initial URL to fetch.
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns list of IPs.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the request is disallowed or resolution fails.
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    
    # GUARD: Accept only HTTP or HTTPS on default port
    if scheme not in ['http', 'https']:
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got: {scheme}")
    
    default_port = {'http': 80, 'https': 444}[scheme]
    actual_port = parsed_url.port
    if actual_port is None:
        actual_port = default_port
    
    if actual_port != default_port:
        raise ValueError(f"Only default ports are allowed for {scheme}, got port {actual_port}")
    
    # GUARD: Resolve the hostname before making the request
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("URL must contain a hostname")
    
    try:
        resolved_ips = resolve_host(hostname)
    except ValueError:
        raise ValueError(f"DNS resolution failed for: {hostname}")
    
    if not resolved_ips:
        raise ValueError("No IP addresses resolved for: {hostname}")
    
    # Helper to validate and resolve URL
    def validate_and_resolve_url(current_url, base_scheme, base_port, base_dns, base_public_addr):
        """
        Validate the URL against constraints and resolve its hostname.
        Returns (resolved_url, resolved_hostname, resolved_ip, is_valid).
        """
        try:
            parsed = urllib.parse.urlparse(current_url)
        except Exception:
            return None, None, None, False
        
        # Check scheme
        if parsed.scheme.lower() != base_scheme:
            return None, None, None, False
        
        # Check port
        if parsed.port is None:
            port = base_port
        else:
            port = parsed.port
        
        if port != base_port:
            return None, None, None, False
        
        # Check credentials (user/pass) - must match
        if parsed.username is not None or parsed.password is not None:
            if parsed.username != base_dns or parsed.password != base_dns:
                # For simplicity in this constrained environment, we assume no credentials or they must match exactly
                # The spec says "same scheme, port, credentials, DNS, and public address"
                # We'll enforce exact match if present
                if parsed.username != base_dns or parsed.password != base_dns:
                    return None, None, None, False
        
        # Check DNS (hostname)
        if parsed.hostname is None:
            return None, None, None, False
        
        if parsed.hostname != base_dns:
            return None, None, None, False
        
        # Check public address (IP)
        if parsed.hostname not in resolved_ips:
            return None, None, None, False
        
        # Resolve the hostname
        try:
            resolved_ips = resolve_host(parsed.hostname)
        except ValueError:
            return None, None, None, False
        
        if not resolved_ips:
            return None, None, None, False
        
        # Reconstruct URL with resolved IP
        new_path = parsed.path
        if parsed.query:
            new_path += '?' + parsed.query
        new_url = f"{parsed.scheme}://{parsed.hostname}:{port}{new_path}"
        
        return new_url, parsed.hostname, resolved_ips[0], True
    
    # Initial validation
    initial_dns = hostname
    initial_ip = resolved_ips[0]
    
    # Follow Location headers (at most 5 hops)
    current_url = url
    location_count = 0
    
    while location_count < 5:
        status, headers, body = transport(current_url)
        
        if status != 200:
            # If not 200, we stop here. The spec says "return the body for status 200".
            # It doesn't explicitly say to raise an error for non-200, but typically we'd stop.
            # However, the plan says "return the response body only for status 200".
            # We assume the caller handles non-200 or we just return what we have if 200, else we might need to raise?
            # Re-reading: "return the body for status 200, and raise ValueError for a disallowed request."
            # Non-200 is not necessarily disallowed, but we only return body if 200.
            # If we don't get 200, we probably shouldn't return anything or raise?
            # Let's assume we stop processing if not 200.
            break
        
        # Process Location headers
        location_headers = headers.get('Location', None)
        if location_headers:
            location_count += 1
            if location_count > 5:
                raise ValueError("Too many Location hops")
            
            # Check if the Location is absolute
            if location_headers.startswith(('http://', 'https://')):
                # It's absolute, use as is
                next_url = location_headers
            else:
                # It's relative, resolve against current_url
                try:
                    base_parsed = urllib.parse.urlparse(current_url)
                    next_parsed = urllib.parse.urljoin(base_parsed.path, location_headers)
                    next_url = f"{base_parsed.scheme}://{base_parsed.hostname}:{base_parsed.port}{next_parsed}"
                except Exception:
                    raise ValueError("Invalid Location header")
            
            # Validate and resolve the new URL
            validated_url, validated_dns, validated_ip, is_valid = validate_and_resolve_url(
                next_url, base_scheme, base_port, initial_dns, initial_ip
            )
            
            if not is_valid:
                raise ValueError("Location header failed validation")
            
            current_url = validated_url
        else:
            break
    
    # Final check: ensure the final resolved URL remains beneath the requested base path
    # This is tricky with relative URLs, but we enforce DNS/IP match which effectively restricts the path scope
    # to the same host. The "beneath" constraint usually implies path prefix matching.
    # Since we enforce same DNS/IP, we are on the same host.
    # We need to check if the final path is a sub-path of the initial path.
    initial_path = parsed_url.path
    final_path = urllib.parse.urlparse(current_url).path
    
    if not final_path.startswith(initial_path):
        # If the path is not a sub-path, it might be invalid.
        # However, if the path is exactly the same or a prefix, it's fine.
        # Example: /a/b vs /a -> /a/b is beneath /a
        # Example: /a vs /a/b -> /a/b is not beneath /a
        if not final_path.startswith(initial_path) and not (initial_path.endswith('/') and final_path.startswith(initial_path + '/')):
            raise ValueError("Final URL path is not beneath the requested base path")
    
    return body
