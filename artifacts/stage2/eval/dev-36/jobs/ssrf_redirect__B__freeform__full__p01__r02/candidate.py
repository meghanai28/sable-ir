import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict security checks.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string if status is 200.
    
    Raises:
        ValueError: If the scheme is not http/https, if DNS lookup fails, or if status is not 200.
    """
    # Parse the initial URL
    try:
        parsed_url = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL: {e}")

    # Validate scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError(f"Unsupported scheme: {parsed_url.scheme}")

    # Resolve hostname to IP addresses
    hostname = parsed_url.hostname
    if not hostname:
        raise ValueError("URL must have a hostname")
    
    ip_addresses = resolve_host(hostname)
    if not ip_addresses:
        raise ValueError(f"DNS lookup failed for {hostname}")

    # Determine the target scheme and port for redirect checks
    target_scheme = parsed_url.scheme
    target_port = parsed_url.port if parsed_url.port else (80 if target_scheme == 'http' else 443)

    # Current URL state
    current_url = parsed_url
    current_scheme = target_scheme
    current_port = target_port
    current_hostname = hostname

    # Follow redirects (at most 5)
    max_redirects = 5
    redirects_count = 0

    while True:
        # If we've followed redirects and still have more, stop (though we check status below)
        if redirects_count >= max_redirects:
            raise ValueError("Too many redirects")

        # Build the request using urllib which handles encoding safely
        # We use the current_url as the base for the request
        request = urllib.request.Request(current_url)
        
        # Resolve the hostname again for this request to ensure it's valid
        # Note: For the initial request, we already checked. For redirects, we check the new hostname.
        req_hostname = request.get_full_url().split('://')[1].split('/')[0]
        if not req_hostname:
            raise ValueError("Invalid hostname in request")
        
        # Re-resolve to ensure DNS is still valid (though usually same host)
        # The spec says "Resolve the url's hostname to its IP address(es) before creating the TCP connection"
        # We assume resolve_host handles the lookup.
        valid_ips = resolve_host(req_hostname)
        if not valid_ips:
            raise ValueError(f"DNS lookup failed for {req_hostname}")

        # Call transport
        try:
            status, headers, body = transport(current_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")

        # Check status code
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")

        # Check for Location header to follow redirects
        location_header = headers.get('Location')
        if location_header:
            redirects_count += 1
            # Parse the Location header
            try:
                location_parsed = urllib.parse.urlparse(location_header)
            except Exception:
                raise ValueError(f"Invalid Location header format: {location_header}")

            # Validate Location scheme
            if location_parsed.scheme not in ('http', 'https'):
                raise ValueError(f"Location header has unsupported scheme: {location_parsed.scheme}")

            # Check if the scheme and port match the current URL
            if location_parsed.scheme != current_scheme:
                raise ValueError(f"Redirect to different scheme not allowed: {location_parsed.scheme} != {current_scheme}")
            
            if location_parsed.port:
                if location_parsed.port != current_port:
                    raise ValueError(f"Redirect to different port not allowed: {location_parsed.port} != {current_port}")
            else:
                # If no port specified in Location, it defaults to the scheme's default
                if current_scheme == 'http' and current_port != 80:
                    raise ValueError(f"Redirect to default port not allowed: {current_port} != 80")
                if current_scheme == 'https' and current_port != 443:
                    raise ValueError(f"Redirect to default port not allowed: {current_port} != 443")

            # Resolve the new hostname
            new_hostname = location_parsed.hostname
            if not new_hostname:
                raise ValueError(f"Location header has no hostname: {location_header}")

            new_ip_addresses = resolve_host(new_hostname)
            if not new_ip_addresses:
                raise ValueError(f"DNS lookup failed for new hostname: {new_hostname}")

            # Update current URL for the next iteration
            current_url = location_header  # Use the raw string for the next transport call
            current_scheme = location_parsed.scheme
            current_port = location_parsed.port if location_parsed.port else (80 if current_scheme == 'http' else 443)
            current_hostname = new_hostname
        else:
            # No redirect, we are done
            break

    return body
