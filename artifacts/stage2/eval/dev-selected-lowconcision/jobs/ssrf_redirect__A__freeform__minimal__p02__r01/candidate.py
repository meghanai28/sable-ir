import socket
import urllib.parse
import urllib.request
import urllib.error

def resolve_host(hostname):
    try:
        return socket.getaddrinfo(hostname, None)[0][4][0]
    except (socket.gaierror, socket.herror):
        raise ValueError(f"Could not resolve hostname: {hostname}")

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(f"Only http and https schemes are allowed, got {scheme}")
    
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL: missing hostname")
    
    resolved_ips = resolve_host(hostname)
    
    # Open the request
    try:
        opener = urllib.request.build_opener()
        req = urllib.request.Request(url)
        response = opener.open(req, timeout=30)
        
        status = int(response.status)
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        # Check for redirects
        while True:
            headers = dict(response.headers)
            location = headers.get('Location')
            
            if location:
                new_url = urllib.parse.urljoin(parsed.getfull_url(), location)
                new_parsed = urllib.parse.urlparse(new_url)
                
                # Validate redirect target
                if new_parsed.scheme.lower() != scheme or new_parsed.hostname != hostname:
                    raise ValueError(f"Redirect to different scheme or host not allowed")
                
                # Update URL for next iteration
                url = new_url
                response = opener.open(urllib.request.Request(url), timeout=30)
            else:
                break
        
        return response.read().decode('utf-8')
    
    except urllib.error.HTTPError as e:
        if e.code != 200:
            raise ValueError(f"Request failed with status {e.code}")
        return e.read().decode('utf-8')
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")
