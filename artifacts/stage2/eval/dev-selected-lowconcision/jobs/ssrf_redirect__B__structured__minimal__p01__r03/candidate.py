def fetch_text(url, transport, resolve_host):
    """
    Fetch text content from a URL using the provided transport and hostname resolver.
    
    Args:
        url (str): The URL to fetch.
        transport (callable): A function taking a URL and returning (status, headers, body).
        resolve_host (callable): A function taking a hostname and returning list of IP addresses.
    
    Returns:
        str: The body of the response for status 200.
    
    Raises:
        ValueError: If the scheme is not http or https, or if no IP is resolved.
    """
    scheme, rest = url.split("://", 1)
    
    if scheme not in ("http", "https"):
        raise ValueError("Only http and https schemes are allowed")
    
    hostname = rest.split("/")[0]
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for hostname")
    
    first_ip = ip_addresses[0]
    port = None
    path = rest
    
    if scheme == "http":
        port = 80
    else:
        port = 443
    
    full_url = f"{scheme}://{hostname}:{port}{path}"
    status, headers, body = transport(full_url)
    
    if status != 200:
        raise ValueError(f"Expected status 200, got {status}")
    
    return body.decode("utf-8") if isinstance(body, bytes) else body
