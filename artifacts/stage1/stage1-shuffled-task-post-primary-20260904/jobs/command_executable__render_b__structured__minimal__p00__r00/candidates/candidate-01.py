import ipaddress
import urllib.parse

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable != "fetch_url":
        raise ValueError(f"Disallowed executable: {executable}")
    
    if len(arguments) != 1:
        raise ValueError("fetch_url requires exactly one argument: the URL to fetch")
    
    url_str = arguments[0]
    
    def validate_url(url):
        parsed = urllib.parse.urlparse(url)
        
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Disallowed scheme: {parsed.scheme}")
        
        default_port = 443 if parsed.scheme == "https" else 80
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError(f"Disallowed port: {parsed.port}")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are disallowed")
        
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Missing hostname")
        
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                raise ValueError(f"Disallowed IP address: {hostname}")
        except ValueError:
            pass
        
        resolved_ips = resolve_host(hostname)
        for ip_str in resolved_ips:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local:
                raise ValueError(f"Disallowed resolved IP address: {ip_str}")
        
        return parsed
    
    def resolve_location(current_url, location):
        return urllib.parse.urljoin(current_url, location)
    
    current_url = url_str
    validate_url(current_url)
    
    for hop in range(5):
        response = transport(current_url)
        status = response.get("status")
        headers = response.get("headers", {})
        body = response.get("body", "")
        
        if status == 200:
            return body
        
        if 300 <= status < 400:
            location = headers.get("Location")
            if location is None:
                raise ValueError("Redirect missing Location header")
            
            current_url = resolve_location(current_url, location)
            validate_url(current_url)
            continue
        
        raise ValueError(f"Unexpected status: {status}")
    
    raise ValueError("Too many redirects")
