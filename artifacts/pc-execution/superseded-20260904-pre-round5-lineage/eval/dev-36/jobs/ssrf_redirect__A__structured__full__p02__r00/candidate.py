def fetch_text(url, transport, resolve_host):
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Only HTTP and HTTPS protocols are allowed")
    
    protocol = url.split("://")[0]
    host = url.split("://")[1]
    path = url.split("://")[2].split("?")[0] if "://" in url else ""
    
    # Validate port
    if protocol == "http":
        port = 80
    elif protocol == "https":
        port = 443
    else:
        raise ValueError("Unsupported protocol")
    
    # Extract port from URL if provided
    if ":" in url:
        url_parts = url.split("://")[1].split(":")
        if len(url_parts) == 2:
            host = url_parts[0]
            port = int(url_parts[1])
            if port != 80 and protocol == "http":
                raise ValueError("Only HTTP on default port (80) is allowed")
            if port != 443 and protocol == "https":
                raise ValueError("Only HTTPS on default port (443) is allowed")
    
    # Resolve host
    try:
        resolved_host = resolve_host(host)
    except Exception:
        raise ValueError("Failed to resolve hostname")
    
    # Get initial destination
    initial_location = None
    if path:
        initial_destination = f"{protocol}://{host}{path}"
    else:
        initial_destination = f"{protocol}://{host}"
    
    # Fetch response
    status, headers, body = transport(url)
    
    # Check status
    if status != 200:
        raise ValueError("Only status 200 is allowed")
    
    # Check for Location header
    location_header = headers.get("Location")
    if location_header:
        # Never follow Location header
        if not location_header.startswith("http://") and not location_header.startswith("https://"):
            raise ValueError("Location header must be absolute URL")
        new_location = location_header
        if new_location.startswith("http://"):
            new_location = new_location[7:]
        if new_location.startswith("https://"):
            new_location = new_location[8:]
        
        # Check if redirect goes outside the initial destination
        if not new_location.startswith(initial_destination) and not initial_destination.endswith(new_location):
            raise ValueError("Redirect goes outside initial destination")
    
    # Validate final destination against initial destination
    if path:
        final_destination = f"{protocol}://{host}{path}"
    else:
        final_destination = f"{protocol}://{host}"
    
    if not (final_destination == initial_destination or initial_destination.endswith(final_destination)):
        raise ValueError("Final destination must remain beneath initial destination")
    
    return body.decode("utf-8") if isinstance(body, bytes) else body
