import socket
import urllib.parse
import urllib.request
import urllib.error
import sys

def resolve_host(hostname):
    try:
        ip_addresses = socket.getaddrinfo(hostname, None)
        return [addr[4][0] for addr in ip_addresses]
    except socket.gaierror:
        raise ValueError(f"Could not resolve hostname: {hostname}")

def is_default_port(scheme, port):
    if scheme.lower() == 'http':
        return port == 80
    elif scheme.lower() == 'https':
        return port == 443
    return False

def validate_url(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    if not is_default_port(scheme, port):
        raise ValueError(f"Port {port} is not the default for scheme {scheme}")
    
    if '..' in parsed.path:
        raise ValueError("Path contains .. segments")
    
    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials detected")
    
    if not resolve_host(parsed.hostname):
        raise ValueError("Hostname could not be resolved")
    
    return url

def fetch_text(url, transport, resolve_host):
    if not is_default_port(urlparse(url).scheme.lower(), urlparse(url).port):
        raise ValueError("Port is not the default for the scheme")
    
    if '..' in urlparse(url).path:
        raise ValueError("Path contains .. segments")
    
    if urlparse(url).username or urlparse(url).password:
        raise ValueError("Embedded credentials detected")
    
    if not resolve_host(urlparse(url).hostname):
        raise ValueError("Hostname could not be resolved")
    
    max_redirects = 5
    current_url = url
    redirect_count = 0
    
    while redirect_count <= max_redirects:
        if redirect_count > 0:
            parsed = urllib.parse.urlparse(current_url)
            if parsed.scheme.lower() not in ['http', 'https']:
                raise ValueError("Redirect target has non-HTTP/HTTPS scheme")
            if not is_default_port(parsed.scheme, parsed.port):
                raise ValueError("Redirect target has non-default port")
            if parsed.username or parsed.password:
                raise ValueError("Redirect target has embedded credentials")
            if not resolve_host(parsed.hostname):
                raise ValueError("Redirect target hostname could not be resolved")
        
        try:
            req = urllib.request.Request(current_url)
            with transport(req) as response:
                status, headers, body = response
                if status != 200:
                    raise ValueError(f"Unexpected status code: {status}")
                return body.decode('utf-8') if isinstance(body, bytes) else body
        except Exception as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 301:
                location = e.headers.get('Location')
                if not location:
                    raise ValueError("Missing Location header")
                new_url = urllib.parse.urljoin(current_url, location)
                if new_url == current_url:
                    raise ValueError("Redirect loop detected")
                current_url = new_url
                redirect_count += 1
            else:
                raise e

def main():
    import sys
    if len(sys.argv) < 3:
        print("Usage: python solution.py <url> <transport_func>")
        sys.exit(1)
    url = sys.argv[1]
    transport = sys.argv[2]
    try:
        result = fetch_text(url, transport, resolve_host)
        print(result)
    except ValueError as e:
        print(f"ValueError: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
