import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url: str, transport, resolve_host) -> str:
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Parse initial URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    # Validate port (default ports)
    default_port = {'http': 80, 'https': 443}
    if parsed.port is None:
        parsed = parsed._replace(port=default_port[parsed.scheme])
    elif parsed.port not in default_port[parsed.scheme]:
        raise ValueError("Only default ports are allowed")
    
    # Resolve and check hostname
    try:
        hostname = parsed.hostname
        if not hostname:
            raise ValueError("Invalid URL format")
        
        resolved_ips = resolve_host(hostname)
        if not resolved_ips:
            raise ValueError("Resolve host failed")
        
        # Ensure resolved IPs are valid (basic check)
        for ip in resolved_ips:
            if not ip or not ip.isdigit():
                raise ValueError("Invalid IP address")
    except Exception as e:
        raise ValueError(f"Invalid hostname: {e}")
    
    # Build initial request URL
    initial_url = parsed._replace(path=url.split('?', 1)[1] if '?' in url else url)
    if not initial_url.path:
        initial_url = initial_url._replace(path='/')
    
    # Follow redirects with limit of 5
    redirect_count = 0
    current_url = initial_url
    
    while True:
        # Check redirect limit
        if redirect_count > 5:
            raise ValueError("Too many redirects")
        
        # Prepare request
        req = urllib.request.Request(current_url, method='GET')
        
        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                headers = response.headers
                body = response.read().decode('utf-8')
                
                if status != 200:
                    raise ValueError(f"Unexpected status code: {status}")
                
                return body
                
        except urllib.error.HTTPError as e:
            status = e.code
            headers = e.headers
            body = e.read().decode('utf-8')
            
            if status != 200:
                raise ValueError(f"Unexpected status code: {status}")
            
            return body
            
        except urllib.error.URLError as e:
            raise ValueError(f"Network error: {e}")
        
        # Handle redirects
        location = headers.get('Location')
        if not location:
            break
        
        redirect_count += 1
        
        # Parse redirect URL
        try:
            redirect_parsed = urllib.parse.urlparse(location)
        except Exception:
            raise ValueError("Invalid redirect URL")
        
        # Check scheme, port, credentials, DNS, and public address
        if redirect_parsed.scheme != parsed.scheme:
            raise ValueError("Redirect scheme mismatch")
        
        if redirect_parsed.port != parsed.port:
            raise ValueError("Redirect port mismatch")
        
        if parsed.username and redirect_parsed.username != parsed.username:
            raise ValueError("Redirect credentials mismatch")
        
        if parsed.password and redirect_parsed.password != parsed.password:
            raise ValueError("Redirect credentials mismatch")
        
        # Resolve new hostname
        new_hostname = redirect_parsed.hostname
        if not new_hostname:
            raise ValueError("Invalid redirect hostname")
        
        new_resolved_ips = resolve_host(new_hostname)
        if not new_resolved_ips:
            raise ValueError("Resolve host failed for redirect")
        
        for ip in new_resolved_ips:
            if not ip or not ip.isdigit():
                raise ValueError("Invalid IP address in redirect")
        
        # Check DNS resolution matches (same public address)
        # This is a simplified check; in practice, you'd compare the resolved IPs
        if set(resolved_ips) != set(new_resolved_ips):
            raise ValueError("DNS resolution mismatch")
        
        # Update current URL
        current_url = redirect_parsed._replace(path=redirect_parsed.path)
        if not current_url.path:
            current_url = current_url._replace(path='/')
    
    return body
