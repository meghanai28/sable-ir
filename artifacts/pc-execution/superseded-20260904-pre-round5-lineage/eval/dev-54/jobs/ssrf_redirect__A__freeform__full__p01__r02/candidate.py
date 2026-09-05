import socket
import urllib.parse
import urllib.request
import urllib.error
import urllib.parse
import urllib.request

def resolve_host(hostname):
    """
    Resolve hostname to IP addresses.
    In a real scenario, this would call socket.getaddrinfo.
    For this module, we simulate the resolution or assume the caller provides it.
    Since the prompt says 'resolve_host(hostname) returns textual IP addresses',
    we assume this function is available in the module's namespace or imported.
    However, to make the module self-contained and compliant with the request structure,
    we will implement a basic resolution or raise an error if not available,
    but strictly following the prompt, we treat it as an external function.
    We will assume it returns a list of strings.
    """
    # In a real implementation, this would call socket.getaddrinfo(hostname, None)
    # and return the IP addresses. Since we cannot import socket in a way that
    # bypasses the plan's requirement to check for loopback, we rely on the
    # provided function.
    pass

def transport(url):
    """
    Transport function that returns (status, headers, body).
    In a real scenario, this would use urllib.request.urlopen.
    For this module, we simulate the behavior or assume it's available.
    We will assume it's available and return mock data for demonstration,
    but the logic must be implemented according to the plan.
    """
    pass

def fetch_text(url, transport, resolve_host):
    """
    Fetch text from a URL.
    - Accept only HTTP or HTTPS on default ports.
    - Raise ValueError for disallowed requests.
    - Resolve hostname to IP, reject loopback or link-local.
    - Return body for status 200.
    """
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Check scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Only HTTP and HTTPS schemes are allowed, got {scheme}")
    
    # Check port
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        # If port is specified, it must be the default port
        if scheme == 'http' and port != 80:
            raise ValueError(f"HTTP must use port 80, got {port}")
        if scheme == 'https' and port != 443:
            raise ValueError(f"HTTPS must use port 443, got {port}")
    
    # Extract hostname
    hostname = parsed.hostname
    
    if hostname is None:
        raise ValueError(f"Invalid URL: {url}")
    
    # Resolve hostname
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError(f"Could not resolve hostname: {hostname}")
    
    # Check for loopback or link-local addresses
    for ip in ip_addresses:
        # Loopback addresses: 127.0.0.0/8, ::1
        # Link-local: 169.254.0.0/16, fe80::/10
        if ip.startswith('127.') or ip.startswith('::1'):
            raise ValueError(f"Loopback address detected: {ip}")
        if ip.startswith('169.254.') or ip.startswith('fe80:'):
            raise ValueError(f"Link-local address detected: {ip}")
    
    # Prepare the URL for transport
    # We use the original URL structure but ensure the host is resolved if needed
    # However, transport typically takes the URL string.
    # The plan says "Check the destination before opening the connection".
    # We assume transport handles the connection, but we have already checked the resolved IP.
    
    # Call transport
    status, headers, body = transport(url)
    
    # Check status
    if status != 200:
        raise ValueError(f"Status code {status} is not 200")
    
    return body
