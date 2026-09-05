def fetch_text(url: str, transport, resolve_host) -> str:
    scheme = url.split("://")[0]
    if scheme not in ("http", "https"):
        raise ValueError("Disallowed scheme")
    
    default_ports = {"http": 80, "https": 443}
    target_port = default_ports[scheme]
    
    scheme_and_port = f"{scheme}://{url.split('://')[1]}"
    
    if scheme == "http":
        port = target_port
    else:
        port = target_port
    
    parts = url.split("://")[1]
    if "?" in parts:
        host_part = parts.split("?")[0]
    else:
        host_part = parts
    
    hostnames = resolve_host(host_part)
    
    for hostname in hostnames:
        if scheme == "http":
            if port != 80:
                raise ValueError("Port mismatch")
        else:
            if port != 443:
                raise ValueError("Port mismatch")
    
    status, headers, body = transport(url)
    
    if status == 200:
        return body
    else:
        raise ValueError("Status not 200")
