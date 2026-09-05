import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the URL
    parsed = urllib.parse.urlparse(url)
    
    # Validate scheme
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Extract host and port
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL: missing host")
    
    port = parsed.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    
    # Normalize host (lowercase)
    host = host.lower()
    
    # Validate host format (basic check for letters, digits, hyphens, dots)
    if not host or not host.replace('.', '').replace('-', '').isalnum():
        raise ValueError(f"Invalid host format: {host}")
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(host)
    except Exception as e:
        raise ValueError(f"Failed to resolve host: {e}")
    
    if not ip_addresses:
        raise ValueError(f"resolve_host returned no IP addresses for {host}")
    
    # Track hops for redirect limit
    max_hops = 5
    current_url = url
    hop_count = 0
    
    # Handle redirects
    while True:
        # Check if we've exceeded hops
        if hop_count > max_hops:
            raise ValueError(f"Too many redirects: {hop_count + 1} hops")
        
        # Parse current URL
        current_parsed = urllib.parse.urlparse(current_url)
        
        # Check for embedded credentials in the URL (security check)
        if current_parsed.username or current_parsed.password:
            raise ValueError("Embedded credentials in URL not allowed")
        
        # Check scheme, host, and port
        current_scheme = current_parsed.scheme.lower()
        current_host = current_parsed.hostname
        
        if current_scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme in redirect: {current_scheme}")
        
        if not current_host:
            raise ValueError(f"Invalid host in redirect: {current_url}")
        
        # Validate host format
        if not current_host.replace('.', '').replace('-', '').isalnum():
            raise ValueError(f"Invalid host format in redirect: {current_host}")
        
        # Resolve hostname for this hop
        try:
            resolved_ips = resolve_host(current_host)
        except Exception as e:
            raise ValueError(f"Failed to resolve host in redirect: {e}")
        
        if not resolved_ips:
            raise ValueError(f"resolve_host returned no IP addresses for {current_host} in redirect")
        
        # Check if this is the final request (no query string or fragment that suggests further processing, 
        # but primarily we rely on the loop termination condition based on status code)
        # For this implementation, we proceed to make the request
        
        # Determine the port to use
        final_port = port
        if current_parsed.port:
            final_port = current_parsed.port
        
        # Create the request
        request = urllib.request.Request(current_url)
        
        # Open the connection
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status = int(response.status)
                headers = dict(response.headers)
                body = response.read().decode('utf-8')
                
                if status != 200:
                    raise ValueError(f"Status code not 200: {status}")
                
                return body
        except urllib.error.HTTPError as e:
            status = e.code
            headers = dict(e.headers)
            body = e.read().decode('utf-8')
            
            if status != 200:
                raise ValueError(f"Status code not 200: {status}")
            
            return body
        except urllib.error.URLError as e:
            raise ValueError(f"Network error: {e}")
        
        # Check for redirects
        location = response.getheader('Location')
        if location:
            hop_count += 1
            # Parse the redirect location
            redirect_url = urllib.parse.urlparse(location)
            
            # Handle relative URLs in redirects
            if not redirect_url.scheme:
                # Use the scheme and host from the current request
                redirect_url = current_parsed._replace(scheme=current_scheme, netloc=current_parsed.netloc)
                redirect_url = redirect_url._replace(path=location)
            
            # Check for infinite redirect loop (basic check)
            if redirect_url.netloc == current_parsed.netloc and redirect_url.path == current_parsed.path:
                raise ValueError("Infinite redirect loop detected")
            
            current_url = redirect_url.geturl()
        else:
            break
    
    # If we reach here without returning, something went wrong
    raise ValueError("Unexpected flow termination")
