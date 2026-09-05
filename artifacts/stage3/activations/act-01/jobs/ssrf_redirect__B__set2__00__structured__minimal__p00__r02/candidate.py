import urllib.request
import urllib.parse
import urllib.error
import socket
import sys

def resolve_host(hostname):
    try:
        return socket.getaddrinfo(hostname, None)[0][4][0]
    except socket.gaierror:
        raise ValueError(f"Failed to resolve hostname: {hostname}")

def fetch_text(url, transport, resolve_host):
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    port = parsed.port
    
    default_port_map = {'http': 80, 'https': 443}
    
    if scheme in ('http', 'https'):
        if port is None:
            port = default_port_map[scheme]
        if port != default_port_map[scheme]:
            raise ValueError(f"Disallowed port {port} for scheme {scheme}")
    
    current_url = url
    max_redirects = 5
    redirect_count = 0
    
    while True:
        if redirect_count > 0:
            if not isinstance(current_url, str):
                raise ValueError("Redirect target must be a string")
            
            if '..' in current_url:
                raise ValueError("URL contains .. segments")
            
            if '@' in current_url:
                raise ValueError("URL contains embedded credentials")
            
            try:
                resolved = resolve_host(current_url)
                if not isinstance(resolved, str) or resolved == '':
                    raise ValueError("Resolved hostname is invalid")
            except ValueError:
                raise ValueError(f"Redirect target resolves to invalid IP or fails resolution: {current_url}")
        
        try:
            response = transport(current_url)
        except Exception as e:
            raise ValueError(f"Request failed: {e}")
        
        status, headers, body = response
        
        if status != 200:
            raise ValueError(f"Unexpected status code: {status}")
        
        if 'Location' in headers:
            location = headers['Location']
            redirect_count += 1
            if redirect_count > max_redirects:
                raise ValueError(f"Too many redirects: {redirect_count}")
            current_url = location
            continue
        
        return body

def main():
    if len(sys.argv) < 3:
        print("Usage: python fetch_text.py <url> <transport_function> <resolve_host_function>")
        sys.exit(1)
    
    url = sys.argv[1]
    transport = sys.argv[2]
    resolve_host = sys.argv[3]
    
    try:
        result = fetch_text(url, transport, resolve_host)
        print(result)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
