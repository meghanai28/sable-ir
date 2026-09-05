import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetch text from a URL with validation and redirect handling.
    
    Args:
        url: The URL to fetch.
        transport: A callable transport(url) -> (status, headers, body).
        resolve_host: A callable resolve_host(hostname) -> list of textual IP addresses.
    
    Returns:
        The body text for a successful (200) response.
    
    Raises:
        ValueError: If the scheme/port is invalid, hostname fails to resolve,
                    or redirect security rules are violated.
    """
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    port = parsed_url.port
    hostname = parsed_url.hostname
    
    # GUARD: Check scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    default_port = {'http': 80, 'https': 443}[scheme]
    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError(f"Non-default port {port} for scheme {scheme}")
    
    # GUARD: Resolve hostname
    try:
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError(f"Hostname {hostname} did not resolve to any IP address")
    except Exception as e:
        raise ValueError(f"Failed to resolve hostname {hostname}: {e}")
    
    # Prepare the base request
    # We need to handle the path correctly, especially if it's empty or has query params
    # urllib.request.urljoin is helpful here, but we need to be careful about the scheme/port
    # We'll construct the full URL to pass to transport if needed, or use urllib.request which handles this.
    # However, the prompt says transport(url) returns (status, headers, body).
    # So we must call transport(url) directly.
    
    # We will use a loop to handle redirects.
    # We need to track the number of hops.
    # The initial request is hop 0.
    
    current_url = url
    hop_count = 0
    
    # We need to keep track of the scheme and port of the initial destination for redirect validation
    initial_scheme = scheme
    initial_port = port
    
    while True:
        # Check if we are following a redirect
        if hop_count > 0:
            # Check for redirect
            # We need to parse the current_url to get the location header if it's a redirect
            # But the transport returns (status, headers, body).
            # We need to check the status code.
            # Wait, the transport function is provided by the caller.
            # We need to call transport(current_url) to get the response.
            # But we need to know if it's a redirect.
            # The prompt says "follow redirects for at most five hops".
            # This implies we make 5 additional requests after the initial one? Or total 5?
            # "follow redirects for at most five hops" usually means the chain of redirects is at most 5.
            # So total requests = 1 (initial) + 5 (redirects) = 6 max?
            # Or does it mean the number of redirects is limited to 5?
            # Let's assume the number of redirect hops is limited to 5.
            # So if we have 5 redirects, we have made 6 requests total.
            pass
        
        # Call transport
        status, headers, body = transport(current_url)
        
        # Check status code
        if status == 200:
            return body
        
        # Check for redirect
        if 'location' in headers:
            location = headers['location']
            
            # Parse the location
            try:
                redirect_parsed = urllib.parse.urlparse(location)
            except Exception as e:
                raise ValueError(f"Invalid redirect URL: {location}")
            
            # Check redirect security rules
            # 1. Same scheme and port as initial destination
            if redirect_parsed.scheme.lower() != initial_scheme:
                raise ValueError(f"Redirect to different scheme: {redirect_parsed.scheme} != {initial_scheme}")
            
            if redirect_parsed.port is None:
                redirect_port = default_port
            else:
                redirect_port = redirect_parsed.port
            
            if redirect_port != initial_port:
                raise ValueError(f"Redirect to different port: {redirect_port} != {initial_port}")
            
            # 2. Does not start with javascript: or data:
            if redirect_parsed.scheme.lower() in ('javascript', 'data'):
                raise ValueError(f"Redirect to unsafe scheme: {redirect_parsed.scheme}")
            
            # 3. Resolve the hostname
            redirect_hostname = redirect_parsed.hostname
            if not redirect_hostname:
                raise ValueError(f"Redirect URL has no hostname: {location}")
            
            try:
                resolved_ips = resolve_host(redirect_hostname)
                if not resolved_ips:
                    raise ValueError(f"Redirect hostname {redirect_hostname} did not resolve")
            except Exception as e:
                raise ValueError(f"Failed to resolve redirect hostname {redirect_hostname}: {e}")
            
            # 4. Count hops
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Too many redirects")
            
            # Update current_url
            current_url = location
        else:
            # Not a redirect, not 200, not disallowed.
            # The prompt says "return the body for status 200, and raise ValueError for a disallowed request".
            # It doesn't specify behavior for non-200 non-redirect.
            # But typically, we should raise an error if we don't get 200.
            # However, the plan says "raise ValueError for a disallowed request".
            # Let's assume non-200 responses are not disallowed but also not successful.
            # But the effect is "return the body text of the validated request whose final status is 200".
            # So if we don't get 200, we should probably raise an error or return the body?
            # The prompt says "return the body for status 200".
            # So if status != 200, we should not return the body.
            # But what to do? Raise ValueError?
            # The plan says "raise ValueError for a disallowed request".
            # A non-200 response is not a disallowed request, but it's not successful.
            # Let's assume we raise ValueError if we don't get 200.
            raise ValueError(f"Request did not return status 200: {status}")
    
    # This should not be reached
    raise ValueError("Unexpected flow")
