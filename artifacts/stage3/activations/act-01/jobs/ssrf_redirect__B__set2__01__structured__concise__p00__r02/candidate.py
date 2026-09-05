import socket
from urllib.parse import urlparse, unquote, parse_qs
import urllib.request

def fetch_text(url: str, transport, resolve_host) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    port = parsed.port
    if port is None:
        port = 80 if scheme == 'http' else 443
    
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL: missing host")
    
    # Check for embedded credentials
    if parsed.username or parsed.password:
        raise ValueError("Embedded credentials are not allowed")
    
    # Check for absolute URLs (already handled by urlparse but explicit check for .. segments in path)
    if '..' in parsed.path:
        raise ValueError("Path contains .. segments")
    
    # Validate scheme and host combination (already valid if we got here)
    
    # Resolve host
    ip_addresses = resolve_host(host)
    if not ip_addresses:
        raise ValueError("Could not resolve host")
    
    if not isinstance(ip_addresses, list):
        ip_addresses = [ip_addresses]
    
    # Check IP addresses for link-local, loopback, multicast
    valid_ips = []
    for ip in ip_addresses:
        ip = ip.strip()
        if ip.startswith(('10.', '192.168.', '169.254.', '::1', '0:0:0:0:0:0:0:0')):
            raise ValueError(f"Invalid IP address: {ip} (link-local, loopback, or multicast)")
        valid_ips.append(ip)
    
    if not valid_ips:
        raise ValueError("No valid IP addresses found")
    
    # Prepare initial request
    final_url = url
    max_redirects = 5
    redirect_count = 0
    
    while redirect_count < max_redirects:
        # Parse current URL for headers
        current_parsed = urlparse(final_url)
        request_url = current_parsed._replace(path='', query='', fragment='').geturl()
        
        # Build request URL
        if current_parsed.scheme == 'http':
            request_url = f"http://{host}"
        else:
            request_url = f"https://{host}"
        
        # Construct full request URL with path, query, fragment
        if current_parsed.path:
            request_url += current_parsed.path
        if current_parsed.query:
            request_url += f"?{current_parsed.query}"
        if current_parsed.fragment:
            request_url += f"#{current_parsed.fragment}"
        
        # Make request
        req = urllib.request.Request(request_url, method='GET')
        try:
            response = transport(final_url)
        except Exception as e:
            raise ValueError(f"Transport error: {e}")
        
        status, headers, body = response
        
        if status != 200:
            # Check for redirect
            if 'location' in headers:
                redirect_url = headers['location']
                redirect_count += 1
                
                # Validate redirect target
                redirect_parsed = urlparse(redirect_url)
                
                # Check scheme
                if redirect_parsed.scheme not in ('http', 'https'):
                    raise ValueError(f"Invalid redirect scheme: {redirect_parsed.scheme}")
                
                # Check for embedded credentials
                if redirect_parsed.username or redirect_parsed.password:
                    raise ValueError("Embedded credentials in redirect not allowed")
                
                # Check for .. segments
                if '..' in redirect_parsed.path:
                    raise ValueError("Redirect path contains .. segments")
                
                # Check port
                redirect_port = redirect_parsed.port
                if redirect_port is None:
                    redirect_port = 80 if redirect_parsed.scheme == 'http' else 443
                
                # Check host
                redirect_host = redirect_parsed.hostname
                if not redirect_host:
                    raise ValueError("Invalid redirect URL: missing host")
                
                # Resolve new host
                new_ip_addresses = resolve_host(redirect_host)
                if not new_ip_addresses:
                    raise ValueError(f"Could not resolve redirect host: {redirect_host}")
                
                if not isinstance(new_ip_addresses, list):
                    new_ip_addresses = [new_ip_addresses]
                
                # Check IP addresses
                valid_new_ips = []
                for ip in new_ip_addresses:
                    ip = ip.strip()
                    if ip.startswith(('10.', '192.168.', '169.254.', '::1', '0:0:0:0:0:0:0:0')):
                        raise ValueError(f"Invalid redirect IP address: {ip}")
                    valid_new_ips.append(ip)
                
                if not valid_new_ips:
                    raise ValueError("No valid IP addresses found in redirect")
                
                # Update final URL
                final_url = redirect_url
            else:
                raise ValueError(f"Unexpected status code: {status}")
        else:
            return body.decode('utf-8')
    
    raise ValueError("Too many redirects")
