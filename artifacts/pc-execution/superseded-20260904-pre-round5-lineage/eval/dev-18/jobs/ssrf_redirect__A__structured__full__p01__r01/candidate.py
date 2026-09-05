def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL with strict security guards.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): Function(url) -> (status, headers, body) tuple.
        resolve_host (callable): Function(hostname) -> list of textual IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: For disallowed schemes, invalid host resolutions, or redirects.
    """
    from urllib.parse import urlparse, urljoin
    
    # Parse the initial URL
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    base_url = parsed_url.geturl()
    
    # GUARD: Check scheme
    allowed_schemes = ('http', 'https')
    if scheme not in allowed_schemes:
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Resolve hostname
    if netloc:
        ip_addresses = resolve_host(netloc)
        if not ip_addresses:
            raise ValueError("resolve_host did not return textual IP addresses")
        # Use the first IP address for the connection
        resolved_netloc = ip_addresses[0]
    else:
        resolved_netloc = netloc
    
    # Build the base URL for origin checking
    # We need to ensure the final resolved destination remains beneath the requested URL's origin
    # The origin is scheme://netloc
    origin = f"{scheme}://{resolved_netloc}"
    
    def check_origin(url_to_check):
        """Check if a URL is within the same origin."""
        try:
            check_parsed = urlparse(url_to_check)
            # Re-resolve the netloc for the check if it's not resolved yet, 
            # but for this logic, we assume we are working with the resolved netloc for the base.
            # However, the check should be against the original request's origin.
            # The plan says "remains beneath the requested URL's origin".
            # We use the resolved netloc as the origin's netloc.
            return (check_parsed.scheme == scheme and 
                    check_parsed.netloc == resolved_netloc)
        except Exception:
            return False
    
    # Resolve the base URL's netloc if it's not already resolved in the parsed object
    # The parsed_url.netloc might be the original hostname. We need to resolve it.
    # Actually, the plan says "resolve the target's hostname". The target is the URL.
    # We resolved netloc above. Now we need to resolve any subsequent URLs if they are absolute.
    
    # Open the connection
    status, headers, body = transport(url)
    
    # GUARD: Check status
    if status != 200:
        # If it's a redirect (3xx), raise ValueError regardless of Location
        if 300 <= status < 400:
            raise ValueError("Redirect response (3xx) not allowed")
        # If it's not 200 and not a redirect, we might still want to fail or return?
        # The plan says "return the body for status 200". It implies if not 200, we shouldn't return.
        # But strictly, if status is not 200, we should probably raise an error or handle it.
        # The plan says "raise ValueError for a disallowed request". A non-200 is not necessarily disallowed,
        # but the EFFECT is "return the body of the response whose status is 200".
        # If status is not 200, we cannot satisfy the effect.
        # Let's assume non-200 non-redirect implies an error or we just don't return.
        # However, typically in such secure fetchers, non-200 is treated as an error.
        # Let's raise ValueError for non-200 to be safe, or just return None?
        # The plan doesn't specify behavior for non-200. But "raise ValueError for a disallowed request".
        # Is non-200 disallowed? Probably yes in this context.
        raise ValueError(f"Unexpected status code: {status}")
    
    # GUARD: Follow Location header only if relative and final resolved destination remains beneath origin
    # Also: raise ValueError for a redirect response (status 3xx) regardless of Location value.
    # We already checked status 3xx above.
    
    location = headers.get('Location')
    if location:
        # Check if it's relative
        if not location.startswith(('http://', 'https://')):
            # It's relative, resolve it against the base URL
            # Note: The base URL here is the one we are currently fetching (url)
            # But the plan says "follow the Location header only when it is relative and the final resolved destination remains beneath the requested URL's origin"
            # The "requested URL's origin" is the original url's origin.
            # We need to resolve the relative URL against the current URL.
            current_url = url
            try:
                # If the current URL is absolute, use it as base. If relative, use base_url?
                # Usually, if the request was absolute, the base is that absolute URL.
                # But if the request was relative (unlikely for url parameter), use base_url.
                # The plan says "url supplied by the caller". Assume it's absolute.
                resolved_url = urljoin(current_url, location)
            except ValueError:
                raise ValueError("Invalid relative URL")
            
            # Check if the resolved URL is within the origin
            if not check_origin(resolved_url):
                raise ValueError("Redirect destination not within origin")
            
            # Recursively fetch?
            # The plan says "follow the Location header".
            # But wait, the plan also says "raise ValueError for a redirect response (status 3xx) regardless of its Location value".
            # This implies we DO NOT follow redirects.
            # The instruction "follow the Location header only when..." seems contradictory to "raise ValueError for a redirect".
            # Let's re-read carefully: "raise ValueError for a redirect response (status 3xx) regardless of its Location value"
            # This means if status is 3xx, we raise ValueError immediately. We do not follow.
            # So the "follow" instruction might be a red herring or applies to non-3xx?
            # But standard HTTP redirects are 3xx.
            # If status is 200, there is no Location to follow (usually).
            # If status is 301/302, we raise ValueError.
            # So we never actually follow a Location in this implementation because we raise ValueError on 3xx.
            # What if status is 200 and Location is present? (e.g., 302 Moved Temporarily with 200? No, that's not standard).
            # Maybe the plan implies: if we get a 3xx, we raise. If we get 200, we don't care about Location.
            # But what if the plan meant "if we follow a redirect, we check origin"?
            # Given "raise ValueError for a redirect response (status 3xx) regardless of its Location value",
            # it explicitly forbids following redirects.
            # So we do nothing with Location if status is 200.
            pass
    
    # Return the body
    return body.decode('utf-8') if isinstance(body, bytes) else body
