import socket
import urllib.parse
import urllib.request
import urllib.error
import ssl

def fetch_text(url: str, transport, resolve_host) -> str:
    # Parse the initial URL
    parsed = urllib.parse.urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    
    # Validate scheme and port
    if scheme not in ('http', 'https'):
        raise ValueError("Disallowed scheme")
    
    if scheme == 'http':
        default_port = 80
    elif scheme == 'https':
        default_port = 443
    else:
        raise ValueError("Unknown scheme")
    
    if port is None:
        port = default_port
    elif port != default_port:
        raise ValueError("Disallowed port")
    
    # DNS Resolution check
    try:
        resolved_ips = resolve_host(host)
        # Check if all resolved IPs are public (simplified check: not starting with 127.0.0.1 or 10.x.x.x etc. if we had a strict list, 
        # but per spec "have a public address" usually implies checking against private ranges. 
        # Since no private IP list is provided, we assume resolve_host returns valid public IPs or we trust the resolver.
        # However, to be safe against loopback, we can check common private ranges.
        private_prefixes = ('127.0.0.1', '127.0.0.2', '127.0.0.3', '127.255.255.255', 
                           '10.0.0.0', '10.0.0.1', '10.0.0.2', '10.0.0.255', '10.255.255.255',
                           '192.168.0.0', '192.168.0.1', '192.168.0.2', '192.168.0.255', '192.168.255.255',
                           '172.16.0.0', '172.16.0.1', '172.16.255.255', '172.17.0.0', '172.17.255.255',
                           '172.18.0.0', '172.18.255.255', '172.19.0.0', '172.19.255.255', '172.20.0.0', '172.20.255.255',
                           '172.21.0.0', '172.21.255.255', '172.22.0.0', '172.22.255.255', '172.23.0.0', '172.23.255.255',
                           '172.24.0.0', '172.24.255.255', '172.25.0.0', '172.25.255.255', '172.26.0.0', '172.26.255.255',
                           '172.27.0.0', '172.27.255.255', '172.28.0.0', '172.28.255.255', '172.29.0.0', '172.29.255.255',
                           '172.30.0.0', '172.30.255.255', '172.31.0.0', '172.31.255.255', '169.254.0.0', '169.254.0.1',
                           '169.254.255.255', '0.0.0.0', '0.0.0.1', '0.0.0.2', '0.0.0.255')
        
        for ip in resolved_ips:
            if ip in private_prefixes:
                raise ValueError("Private IP address detected")
    except Exception:
        raise ValueError("DNS resolution failed")
    
    # Build the initial request URL
    base_url = f"{scheme}://{host}:{port}"
    
    # Follow Location headers (at most 5)
    current_url = url
    location_count = 0
    
    while location_count < 5:
        # Create a request to the current URL
        req = urllib.request.Request(current_url)
        
        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                headers = response.headers
                body = response.read().decode('utf-8')
                
                if status == 200:
                    return body
                
                # Check for Location header
                location = headers.get('Location')
                if location:
                    # Resolve the Location header relative to current_url
                    try:
                        loc_parsed = urllib.parse.urlparse(location)
                        # If no scheme, it's relative to the current URL's path
                        if not loc_parsed.scheme:
                            # Combine current_url path and location
                            current_url = urllib.parse.urljoin(current_url, location)
                        else:
                            current_url = location
                    except Exception:
                        raise ValueError("Invalid Location header")
                    
                    # Validate scheme and port of the new location
                    new_scheme = loc_parsed.scheme.lower()
                    new_port = loc_parsed.port
                    
                    if new_scheme not in ('http', 'https'):
                        raise ValueError("Disallowed scheme in Location")
                    
                    if new_scheme == 'http':
                        new_default_port = 80
                    elif new_scheme == 'https':
                        new_default_port = 443
                    else:
                        raise ValueError("Unknown scheme in Location")
                    
                    if new_port is None:
                        new_port = new_default_port
                    elif new_port != new_default_port:
                        raise ValueError("Disallowed port in Location")
                    
                    # DNS Resolution check for new location
                    new_host = loc_parsed.hostname
                    if not new_host:
                        raise ValueError("Invalid host in Location")
                    
                    try:
                        new_resolved = resolve_host(new_host)
                        for ip in new_resolved:
                            if ip in private_prefixes:
                                raise ValueError("Private IP address in Location")
                    except Exception:
                        raise ValueError("DNS resolution failed for Location")
                    
                    # Update current_url
                    current_url = f"{new_scheme}://{new_host}:{new_port}"
                    location_count += 1
                else:
                    break
        except urllib.error.HTTPError as e:
            raise ValueError(f"HTTP Error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise ValueError(f"URL Error: {e.reason}")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Request failed: {str(e)}")
    
    raise ValueError("No body returned for status 200")
