import socket
import urllib.parse
import urllib.request
import urllib.error
import urllib.response
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    if not url:
        raise ValueError("Empty URL")
    
    # Parse the URL to extract scheme, netloc, and path
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    hostname = parsed.netloc
    if not scheme:
        # Assume http if no scheme
        scheme = "http"
        hostname = parsed.netloc or "localhost"
    
    # Check scheme
    if scheme not in ("http", "https"):
        raise ValueError(f"Disallowed scheme: {scheme}")
    
    # Resolve hostname
    try:
        ip_addresses = resolve_host(hostname)
    except Exception:
        raise ValueError(f"Failed to resolve hostname: {hostname}")
    
    if not ip_addresses:
        raise ValueError(f"No IP addresses found for: {hostname}")
    
    # Build the request URL with the resolved IP
    # We need to construct a new URL that uses the resolved IP but keeps the original path and query
    # If the original URL had a port, we might need to handle it, but for simplicity we'll use the IP directly
    # We'll construct the full URL by replacing the hostname part
    new_url = f"{scheme}://{hostname}"
    if parsed.path:
        new_url += parsed.path
    if parsed.query:
        new_url += f"?{parsed.query}"
    
    # We need to ensure we don't follow redirects that change the host or scheme
    # We'll use urllib.request with a custom redirect handler that checks the scheme and host
    
    # Create a custom opener that prevents unsafe redirects
    class UnsafeRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            # Parse the new URL
            new_parsed = urllib.parse.urlparse(newurl)
            new_scheme = new_parsed.scheme.lower()
            new_hostname = new_parsed.netloc
            
            # Check if the new scheme is allowed
            if new_scheme not in ("http", "https"):
                raise ValueError(f"Redirect to disallowed scheme: {new_scheme}")
            
            # Check if the hostname changed
            # We need to compare the hostname, ignoring port
            old_hostname = req.get_full_url().split("//")[1].split(":")[0]
            new_hostname_stripped = new_hostname.split(":")[0]
            
            if old_hostname != new_hostname_stripped:
                raise ValueError(f"Redirect to different host: {new_hostname_stripped}")
            
            # If we get here, it's safe to redirect
            return super(UnsafeRedirectHandler, self).redirect_request(req, fp, code, msg, headers, newurl)
    
    # Create opener with our custom handler
    opener = urllib.request.build_opener(UnsafeRedirectHandler())
    
    # Open the URL
    try:
        response = opener.open(new_url)
    except urllib.error.HTTPError as e:
        if e.code != 200:
            raise ValueError(f"HTTP error: {e.code}")
        raise ValueError(f"Unexpected status code: {e.code}")
    except urllib.error.URLError as e:
        raise ValueError(f"URL error: {e.reason}")
    except Exception as e:
        raise ValueError(f"Request failed: {e}")
    
    # Check status code
    if response.status != 200:
        raise ValueError(f"Expected status 200, got {response.status}")
    
    # Read the body
    body = response.read().decode('utf-8')
    return body
