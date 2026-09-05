import urllib.parse
import urllib.request
import urllib.error
import socket
import ssl

def fetch_text(url: str, transport: callable, resolve_host: callable) -> str:
    """
    Fetch text from a URL using the provided transport and hostname resolver.
    
    Args:
        url: The URL to fetch from.
        transport: A function that takes a URL and returns (status, headers, body).
        resolve_host: A function that takes a hostname and returns a list of IP addresses.
    
    Returns:
        The response body as a string for status 200.
    
    Raises:
        ValueError: If the hostname cannot be resolved, the port is invalid,
                    or the status is not 200.
    """
    # Parse the initial URL to get scheme, netloc, and path
    parsed_url = urllib.parse.urlparse(url)
    scheme = parsed_url.scheme.lower()
    netloc = parsed_url.netloc
    path = parsed_url.path
    
    # Validate scheme and port
    if scheme not in ['http', 'https']:
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    port = parsed_url.port
    if port is None:
        if scheme == 'http':
            port = 80
        elif scheme == 'https':
            port = 443
    else:
        # Ensure port is an integer
        if not isinstance(port, int):
            raise ValueError("Invalid port specification.")
    
    # Validate port
    if scheme == 'http' and port != 80:
        raise ValueError("Invalid port for HTTP request.")
    if scheme == 'https' and port != 443:
        raise ValueError("Invalid port for HTTPS request.")
    
    # Resolve hostname
    hostname = netloc.split(':')[0]
    if not hostname:
        raise ValueError("Invalid hostname.")
    
    ips = resolve_host(hostname)
    if not ips:
        raise ValueError(f"Cannot resolve hostname: {hostname}")
    
    # Construct the request URL with the resolved port
    request_url = f"{scheme}://{hostname}:{port}{path}"
    
    # Open the connection
    try:
        request = urllib.request.Request(request_url)
        with urllib.request.urlopen(request) as response:
            status = int(response.status)
            headers = dict(response.headers)
            body = response.read().decode('utf-8')
            
            # Check status code
            if status != 200:
                raise ValueError(f"Status code {status} is not 200.")
            
            # Handle redirects only if status is exactly 200 and location header exists
            location = headers.get('location')
            if location:
                # Check if location is an absolute URL
                if not location.startswith(('http://', 'https://')):
                    # Relative redirect, not allowed per guard spec
                    raise ValueError("Relative redirect not allowed.")
                
                try:
                    redirect_url = urllib.parse.urlparse(location)
                    redirect_scheme = redirect_url.scheme.lower()
                    redirect_netloc = redirect_url.netloc
                    redirect_path = redirect_url.path
                    
                    # Validate redirect scheme
                    if redirect_scheme not in ['http', 'https']:
                        raise ValueError("Invalid scheme in redirect.")
                    
                    # Validate redirect port
                    redirect_port = redirect_url.port
                    if redirect_port is None:
                        if redirect_scheme == 'http':
                            redirect_port = 80
                        elif redirect_scheme == 'https':
                            redirect_port = 443
                    else:
                        if not isinstance(redirect_port, int):
                            raise ValueError("Invalid port in redirect.")
                    
                    if redirect_scheme == 'http' and redirect_port != 80:
                        raise ValueError("Invalid port in redirect.")
                    if redirect_scheme == 'https' and redirect_port != 443:
                        raise ValueError("Invalid port in redirect.")
                    
                    # Resolve redirect hostname
                    redirect_hostname = redirect_netloc.split(':')[0]
                    if not redirect_hostname:
                        raise ValueError("Invalid hostname in redirect.")
                    
                    redirect_ips = resolve_host(redirect_hostname)
                    if not redirect_ips:
                        raise ValueError(f"Cannot resolve redirect hostname: {redirect_hostname}")
                    
                    # Check path remains beneath requested URL's directory
                    # If no path in request, redirect must be absolute and same host
                    if not path:
                        if redirect_netloc != netloc:
                            raise ValueError("Redirect must be to same host.")
                    else:
                        # Parse request path directory
                        request_dir = path.rstrip('/')
                        if not request_dir:
                            request_dir = '/'
                        
                        # Parse redirect path
                        if redirect_path.startswith('/'):
                            redirect_path = redirect_path[1:]
                        if not redirect_path:
                            redirect_path = '/'
                        
                        # Check if redirect path is beneath request path
                        # Simple check: redirect path must start with request path + '/' or be exactly request path
                        if not redirect_path.startswith(request_dir + '/') and redirect_path != request_dir:
                            raise ValueError("Redirect path must remain beneath requested URL's directory.")
                    
                    # Follow redirect
                    request = urllib.request.Request(redirect_url)
                    with urllib.request.urlopen(request) as response:
                        status = int(response.status)
                        headers = dict(response.headers)
                        body = response.read().decode('utf-8')
                        
                        if status != 200:
                            raise ValueError(f"Status code {status} is not 200.")
                        
                        location = headers.get('location')
                        if location:
                            raise ValueError("Redirect loop detected.")
                
                except Exception as e:
                    raise ValueError(f"Redirect validation failed: {e}")
            
            return body
    
    except urllib.error.HTTPError as e:
        raise ValueError(f"HTTP error occurred: {e}")
    except urllib.error.URLError as e:
        raise ValueError(f"URL error occurred: {e}")
    except Exception as e:
        raise ValueError(f"Unexpected error: {e}")
