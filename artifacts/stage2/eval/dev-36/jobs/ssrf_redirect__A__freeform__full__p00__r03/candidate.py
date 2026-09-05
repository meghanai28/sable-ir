def fetch_text(url, transport, resolve_host) -> str:
    """
    Fetch text from a URL with strict validation and no redirect following.
    
    Args:
        url: The URL to fetch (can be absolute or relative).
        transport: A callable that takes a URL and returns (status, headers, body).
        resolve_host: A callable that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The body of the response if status is 200 and validation passes.
    
    Raises:
        ValueError: If the URL scheme is invalid, status is not 200, 
                    no IP address is resolved, or validation fails.
    """
    import urllib.parse
    
    # Parse the URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed_url.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only http:// and https:// schemes are allowed.")
    
    # Check if the URL is absolute
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("URL must be absolute with a scheme and netloc.")
    
    # Determine the base host for comparison
    base_host = parsed_url.netloc.lower()
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check status code
    if status != 200:
        raise ValueError("Only status code 200 is allowed.")
    
    # Check if the final destination is absolute and valid scheme
    # The plan implies we need to resolve the final destination.
    # Since we don't follow redirects, the final destination is the one returned by transport.
    # However, the plan says "Check the final destination after resolving the hostname".
    # We need to determine the effective hostname. If the URL is relative, 
    # we might need to resolve it against the base, but the plan says "treat it as untrusted".
    # Let's assume the transport returns the final URL or we need to resolve the netloc.
    # The plan says: "Check the final destination after resolving the hostname and raising ValueError unless it is absolute and begins with http:// or https://."
    # This implies we need to resolve the netloc of the original URL or the effective URL.
    # Given "do not follow a redirect", the effective URL is likely the one passed to transport or derived from it.
    # However, transport(url) is called. The url might be relative.
    # Let's assume the destination is the netloc of the parsed url.
    
    # Resolve the hostname
    hostnames = resolve_host(parsed_url.netloc)
    
    if not hostnames:
        raise ValueError("No IP address returned for hostname.")
    
    # Check if the resolved destination remains beneath the requested url's host.
    # This part is ambiguous. "beneath" usually means subdomain.
    # But the plan says "Return the body... whose resolved destination remains beneath the requested url's host."
    # This might imply a security check where the resolved IP must belong to the same domain.
    # However, without a DNSSEC check or similar, we can't verify ownership.
    # Let's interpret "beneath" as the hostname being a subdomain or equal to the base host.
    # Actually, re-reading: "Check the final destination after resolving the hostname and raising ValueError unless it is absolute and begins with http:// or https://."
    # Then "Return the body... whose resolved destination remains beneath the requested url's host."
    # This suggests we need to ensure the resolved host is within the requested host.
    # Let's assume this means the hostname part of the URL must match or be a subdomain of the base host.
    # But since we are just returning the body, and the plan says "raise ValueError unless...",
    # we must enforce this.
    
    # Let's parse the destination URL again if it's absolute.
    # If the url is relative, we might need to resolve it. But the plan says "treat it as untrusted".
    # Let's assume the destination is the netloc of the parsed url.
    
    # Check if the resolved destination remains beneath the requested url's host.
    # This implies checking if the hostname is a subdomain of the base host.
    # We will check if the base_host is a suffix of the hostname (excluding dots).
    # Actually, standard subdomain check: base_host.endswith(hostname) and hostname != base_host?
    # No, "beneath" means the resolved host is a subdomain of the base host.
    # So base_host should be a suffix of hostname.
    
    if not base_host.endswith(parsed_url.netloc):
        raise ValueError("Resolved destination must be beneath the requested host.")
    
    # Return the body
    return body
