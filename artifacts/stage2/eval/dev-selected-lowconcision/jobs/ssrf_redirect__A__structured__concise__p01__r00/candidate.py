def fetch_text(url: str, transport, resolve_host) -> str:
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("Only HTTP and HTTPS URLs are allowed")
    
    hostname = url.split("://")[1].split("/")[0]
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("No IP addresses resolved for hostname")
    
    protocol = "http" if url.startswith("http://") else "https"
    port = 80 if protocol == "http" else 443
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body
