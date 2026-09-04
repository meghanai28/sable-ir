import subprocess
import urllib.parse
import ipaddress
from typing import Callable, Tuple

def run_text_utility(executable: str, arguments: list[str]) -> str:
    allowed = {"cat", "head", "tail", "sort", "uniq", "wc", "grep", "sed", "awk", "cut", "tr", "fold", "fmt", "nl", "od", "paste", "pr", "split", "tac", "rev", "join", "comm", "diff", "patch", "expand", "unexpand", "strings", "csplit", "tsort"}
    if executable not in allowed:
        raise ValueError(f"Executable '{executable}' is disallowed")
    result = subprocess.run([executable] + arguments, capture_output=True, text=True, check=True)
    return result.stdout

def fetch_text(url: str, transport: Callable[[str], Tuple[int, dict, str]], resolve_host: Callable[[str], list[str]]) -> str:
    def validate_url(url_to_validate: str) -> urllib.parse.ParseResult:
        parsed = urllib.parse.urlparse(url_to_validate)
        
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme: {parsed.scheme}")
        
        default_port = 80 if parsed.scheme == "http" else 443
        
        if parsed.port is not None and parsed.port != default_port:
            raise ValueError(f"Non-default port not allowed: {parsed.port}")
        
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials in URL are not allowed")
        
        if not parsed.hostname:
            raise ValueError("Missing hostname")
        
        return parsed
    
    def validate_host(hostname: str) -> None:
        try:
            ip_addrs = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve host: {hostname}")
        
        if not ip_addrs:
            raise ValueError(f"No addresses resolved for host: {hostname}")
        
        for addr in ip_addrs:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                raise ValueError(f"Invalid IP address from DNS: {addr}")
            
            if ip.is_private:
                raise ValueError(f"Private IP address not allowed: {addr}")
            if ip.is_loopback:
                raise ValueError(f"Loopback IP address not allowed: {addr}")
            if ip.is_link_local:
                raise ValueError(f"Link-local IP address not allowed: {addr}")
            if ip.is_multicast:
                raise ValueError(f"Multicast IP address not allowed: {addr}")
            if ip.is_reserved:
                raise ValueError(f"Reserved IP address not allowed: {addr}")
            if ip.is_unspecified:
                raise ValueError(f"Unspecified IP address not allowed: {addr}")
            if hasattr(ip, 'is_site_local') and ip.is_site_local:
                raise ValueError(f"Site-local IP address not allowed: {addr}")
    
    current_url = url
    parsed = validate_url(current_url)
    validate_host(parsed.hostname)
    
    hop_count = 0
    
    while True:
        status, headers, body = transport(current_url)
        
        if status == 200:
            return body
        
        if status in (301, 302, 307, 308):
            hop_count += 1
            if hop_count > 5:
                raise ValueError("Too many redirects")
            
            location = headers.get("Location")
            if location is None:
                raise ValueError("Redirect response missing Location header")
            
            current_url = urllib.parse.urljoin(current_url, location)
            parsed = validate_url(current_url)
            validate_host(parsed.hostname)
            continue
        
        raise ValueError(f"Unexpected HTTP status: {status}")
