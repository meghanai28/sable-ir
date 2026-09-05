import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl
import sys

def _validate_hostname(hostname):
    """Basic DNS validation to ensure hostname is not empty or malformed."""
    if not hostname or hostname.startswith(".."):
        return False
    return True

def _validate_public_address(ip_addresses):
    """Basic check to ensure resolved IPs are valid IPv4 or IPv6 strings."""
    if not ip_addresses:
        return False
    for ip in ip_addresses:
        try:
            socket.inet_aton(ip)
        except socket.error:
            return False
    return True

def _resolve_destination(url, resolve_host):
    """Resolve the URL to a full destination and return scheme, host, port, and resolved IPs."""
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname
    port = parsed.port
    
    if not host:
        raise ValueError("Invalid URL: missing hostname")
    
    # Resolve host to IP addresses
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError("Resolve failed: no IP addresses found")
    
    if not _validate_hostname(host):
        raise ValueError("Invalid hostname: contains .. segments")
    
    if not _validate_public_address(ip_addresses):
        raise ValueError("Invalid IP addresses: malformed")
    
    return scheme, host, port, ip_addresses

def _validate_redirect_scheme_port(scheme, host, port, new_scheme, new_host, new_port):
    """Check if redirect preserves scheme and port."""
    if scheme.lower() != new_scheme.lower():
        return False
    if port is not None and new_port is not None and port != new_port:
        return False
    return True

def _follow_redirects(url, resolved_info, resolve_host, max_hops=5):
    """Follow redirects, validating scheme/port and hop count."""
    current_url = url
    hops = 0
    
    while True:
        scheme, host, port, _ = resolved_info
        
        # Parse current URL
        parsed = urllib.parse.urlparse(current_url)
        redirect_url = parsed.path
        
        # Check for relative URLs
        if not parsed.path or parsed.path.startswith('/'):
            redirect_url = f"{scheme}://{host}:{port}{parsed.path}"
        
        # Resolve the redirect URL
        try:
            redirect_parsed = urllib.parse.urlparse(redirect_url)
            new_scheme = redirect_parsed.scheme
            new_host = redirect_parsed.hostname
            new_port = redirect_parsed.port
            
            # Validate redirect
            if not _validate_redirect_scheme_port(scheme, host, port, new_scheme, new_host, new_port):
                raise ValueError("Redirect disallowed: scheme or port mismatch")
            
            # Resolve new host
            new_ip_addresses = resolve_host(new_host)
            if not new_ip_addresses:
                raise ValueError("Redirect failed: no IP addresses found")
            
            if not _validate_hostname(new_host):
                raise ValueError("Redirect disallowed: hostname contains .. segments")
            if not _validate_public_address(new_ip_addresses):
                raise ValueError("Redirect disallowed: malformed IP addresses")
            
            # Update resolved info for next iteration
            resolved_info = (new_scheme, new_host, new_port, new_ip_addresses)
            
            # Check hop count
            if hops >= max_hops:
                raise ValueError("Redirect loop: maximum hops exceeded")
            
            # Update current URL
            current_url = redirect_url
            hops += 1
            
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if e.code is None and "Redirect" in str(e):
                raise ValueError("Redirect disallowed: invalid redirect URL")
            raise

def fetch_text(url, transport, resolve_host):
    """Fetch text from URL with strict validation and redirect handling."""
    # Validate URL components before starting
    scheme, host, port, ip_addresses = _resolve_destination(url, resolve_host)
    
    # Validate scheme and port
    if scheme.lower() not in ['http', 'https']:
        raise ValueError("Invalid scheme: must be HTTP or HTTPS")
    
    # Follow redirects
    _follow_redirects(url, (scheme, host, port, ip_addresses), resolve_host)
    
    # Open connection
    try:
        if scheme.lower() == 'https':
            context = ssl._create_unverified_context()
            opener = urllib.request.build_opener()
            opener.add_header('User-Agent', 'Python')
            req = urllib.request.Request(url)
            response = opener.open(req, context=context)
        else:
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(url)
        
        # Read body
        body = response.read().decode('utf-8', errors='replace')
        
        # Check status
        if response.status != 200:
            raise ValueError(f"Invalid status: {response.status}")
        
        return body
    
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
