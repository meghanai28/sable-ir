import socket
import urllib.parse
import urllib.request
import urllib.error

def fetch_text(url, transport, resolve_host):
    # Parse the initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate scheme
    if parsed_url.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed.")
    
    # Validate port
    if parsed_url.port is None:
        expected_port = 80 if parsed_url.scheme == 'http' else 443
        if parsed_url.port != expected_port:
            raise ValueError("Only default ports are allowed.")
    else:
        if parsed_url.scheme == 'http' and parsed_url.port != 80:
            raise ValueError("Only default ports are allowed.")
        if parsed_url.scheme == 'https' and parsed_url.port != 443:
            raise ValueError("Only default ports are allowed.")
    
    # Resolve initial hostname
    initial_hostname = parsed_url.hostname
    if initial_hostname is None:
        raise ValueError("Invalid URL hostname.")
    
    ips = resolve_host(initial_hostname)
    if not ips:
        raise ValueError("No IP address found for initial hostname.")
    
    current_url = url
    max_redirects = 5
    redirects = 0
    
    while True:
        # Parse current URL
        parsed = urllib.parse.urlparse(current_url)
        
        # Resolve hostname for current URL
        hostname = parsed.hostname
        if hostname is None:
            raise ValueError("Invalid URL hostname.")
        
        ips = resolve_host(hostname)
        if not ips:
            raise ValueError("No IP address found for current hostname.")
        
        # Build request URL
        request_url = f"{parsed.scheme}://{hostname}"
        if parsed.port:
            request_url += f":{parsed.port}"
        request_url += parsed.path
        
        # Make request
        req = urllib.request.Request(request_url)
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            if e.code != 200:
                raise ValueError(f"Unexpected status code: {e.code}")
            body = e.read()
        except urllib.error.URLError as e:
            raise ValueError(f"Request failed: {e.reason}")
        
        status = response.status
        headers = dict(response.headers)
        body = response.read()
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirect
        location = headers.get('Location')
        if location:
            redirects += 1
            if redirects > max_redirects:
                raise ValueError("Too many redirects.")
            
            # Parse Location
            loc_parsed = urllib.parse.urlparse(location)
            
            # Validate Location scheme
            if loc_parsed.scheme not in ('http', 'https'):
                raise ValueError("Redirect Location must have http or https scheme.")
            
            # Validate Location port
            if loc_parsed.port is None:
                expected_port = 80 if loc_parsed.scheme == 'http' else 443
                if loc_parsed.port != expected_port:
                    raise ValueError("Redirect Location must use default port.")
            else:
                if loc_parsed.scheme == 'http' and loc_parsed.port != 80:
                    raise ValueError("Redirect Location must use default port.")
                if loc_parsed.scheme == 'https' and loc_parsed.port != 443:
                    raise ValueError("Redirect Location must use default port.")
            
            # Check if redirect points to different scheme/port than initial destination
            initial_scheme = parsed.scheme
            initial_port = parsed.port or (80 if initial_scheme == 'http' else 443)
            
            if loc_parsed.scheme != initial_scheme:
                raise ValueError("Redirect must point to same scheme.")
            if loc_parsed.port != initial_port:
                raise ValueError("Redirect must point to same port.")
            
            # Resolve Location hostname
            loc_hostname = loc_parsed.hostname
            if loc_hostname is None:
                raise ValueError("Invalid redirect URL hostname.")
            
            loc_ips = resolve_host(loc_hostname)
            if not loc_ips:
                raise ValueError("No IP address found for redirect hostname.")
            
            # Construct new URL
            new_scheme = loc_parsed.scheme
            new_hostname = loc_parsed.hostname
            new_port = loc_parsed.port
            new_path = loc_parsed.path
            
            if new_scheme == 'http':
                if new_port is None:
                    new_port = 80
                new_port_str = f":{new_port}" if new_port else ""
            else:
                if new_port is None:
                    new_port = 443
                new_port_str = f":{new_port}" if new_port else ""
            
            new_url = f"{new_scheme}//{new_hostname}{new_port_str}{new_path}"
            
            # Handle relative paths
            if not new_path.startswith('/'):
                # If path is relative, join with current path
                current_path = parsed.path
                if current_path.endswith('/'):
                    new_path = new_path
                else:
                    new_path = current_path + '/' + new_path
            
            current_url = new_url
        else:
            # No redirect, return body
            break
    
    return body.decode('utf-8')
