def fetch_text(url: str, transport, resolve_host) -> str:
    # Validate scheme
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    scheme = "https" if url.startswith("https://") else "http"
    port = 443 if scheme == "https" else 80
    
    # Extract host and path
    netloc = url.split("://")[1]
    path = url.split("://")[1].split("/")[1] if "/" in url.split("://")[1] else "/"
    
    # Resolve host
    try:
        hostname = netloc.split(":")[0]
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError("Host resolution failed")
    
    if not ip_addresses:
        raise ValueError("Host did not resolve")
    
    # Construct final URL with resolved IP
    final_url = f"{scheme}://{ip_addresses[0]}{path}"
    
    # Check for path escaping or absolute paths
    if ".." in path:
        raise ValueError("Path contains escape sequences")
    
    # Make the request
    status, headers, body = transport(final_url)
    
    # Validate status
    if status != 200:
        raise ValueError(f"Invalid status code: {status}")
    
    return body
