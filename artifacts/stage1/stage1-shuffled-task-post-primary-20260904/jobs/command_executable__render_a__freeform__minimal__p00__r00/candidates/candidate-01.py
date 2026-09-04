import subprocess
import urllib.parse
import ipaddress

ALLOWED_UTILITIES = {"cat", "head", "tail", "grep", "sed", "awk", "sort", "uniq", "wc", "tr", "cut", "paste", "join", "split", "csplit", "fmt", "pr", "fold", "nl", "od", "hexdump", "strings", "diff", "cmp", "comm", "patch", "ed", "ex", "vi", "emacs", "pico", "nano", "joe", "jed", "vim", "less", "more", "pg", "most"}

def resolve_host(hostname: str) -> list[str]:
    result = subprocess.run(["getent", "hosts", hostname], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    ips = []
    for line in result.stdout.strip().split("\n"):
        parts = line.split()
        if parts:
            ips.append(parts[0])
    return ips

def transport(url: str):
    import urllib.request
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "Mozilla/5.0")
    response = urllib.request.urlopen(req)
    return response

def run_text_utility(executable: str, arguments: list[str]) -> str:
    if executable not in ALLOWED_UTILITIES:
        raise ValueError(f"Executable '{executable}' is not allowed")
    result = subprocess.run([executable] + arguments, capture_output=True, text=True, check=True)
    return result.stdout

def fetch_url(url: str) -> bytes:
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    hostname = parsed.hostname
    port = parsed.port
    
    if scheme == "http":
        expected_port = 80
    elif scheme == "https":
        expected_port = 443
    else:
        raise ValueError("Scheme must be http or https")
    
    if port is None:
        port = expected_port
    
    if port != expected_port:
        raise ValueError(f"Port {port} does not match expected port {expected_port} for scheme {scheme}")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_multicast or ip.is_link_local or ip.is_unspecified:
            raise ValueError(f"IP address {ip_str} is not public")
    
    try:
        response = transport(url)
    except Exception as e:
        if hasattr(e, 'code') and 300 <= e.code < 400:
            raise ValueError("Redirects are not followed")
        raise
    
    status = response.getcode()
    
    if 300 <= status < 400:
        raise ValueError("Redirects are not followed")
    
    if status == 200:
        return response.read()
    
    raise ValueError(f"Unexpected status code: {status}")
