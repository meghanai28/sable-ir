import socket
import urllib.parse
import urllib.request
import urllib.error
import urllib.parse

def fetch_text(url: str, transport, resolve_host) -> str:
    """
    Fetches text from a URL with strict validation of hostnames, schemes, and ports.
    Validates against disallowed schemes, embedded credentials, non-public IPs, and excessive redirects.
    """
    
    def is_global_public_ip(ip: str) -> bool:
        """
        Checks if an IP address is a global public address.
        Disallows loopback (127.0.0.1, ::1), link-local, multicast, private ranges, and reserved addresses.
        """
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            return False
        
        # Check for loopback
        if 127 <= nums[0] <= 127:
            return False
        if 0 <= nums[0] <= 255 and 0 <= nums[1] <= 255 and 0 <= nums[2] <= 255 and 255 <= nums[3] <= 255:
            return False
        
        # Check for private ranges (RFC 1918)
        if (10 <= nums[0] <= 10) or \
           (172 <= nums[0] <= 172 and 16 <= nums[1] <= 31) or \
           (192 <= nums[0] <= 192 and 168 <= nums[1] <= 168) or \
           (224 <= nums[0] <= 239):
            return False
            
        # Check for link-local (169.254/10)
        if 169 == nums[0] and 254 == nums[1]:
            return False
            
        # Check for multicast (224-239)
        if 224 <= nums[0] <= 239:
            return False
            
        # Check for reserved (0.0.0.0)
        if nums[0] == 0:
            return False
            
        return True

    def validate_url(parsed_url: urllib.parse.ParseResult) -> None:
        """
        Validates the URL structure:
        - Must have a hostname.
        - No username or password.
        - Scheme must be HTTP or HTTPS.
        - Port must be omitted, 80 (HTTP), or 443 (HTTPS).
        """
        if not parsed_url.hostname:
            raise ValueError("URL must have a hostname")
            
        if parsed_url.username is not None or parsed_url.password is not None:
            raise ValueError("URL cannot contain username or password")
            
        scheme = parsed_url.scheme.lower()
        if scheme not in ('http', 'https'):
            raise ValueError(f"Disallowed scheme: {scheme}")
            
        port = parsed_url.port
        if port is not None:
            if scheme == 'http' and port != 80:
                raise ValueError(f"HTTP requires port 80, got {port}")
            if scheme == 'https' and port != 443:
                raise ValueError(f"HTTPS requires port 443, got {port}")
        else:
            # Default port check
            if scheme == 'http' and port != 80:
                raise ValueError(f"HTTP requires port 80")
            if scheme == 'https' and port != 443:
                raise ValueError(f"HTTPS requires port 443")

    def resolve_and_validate_hostname(hostname: str) -> str:
        """
        Resolves hostname to IP and validates it is a global public address.
        Returns the first valid IP address.
        """
        try:
            addrs = resolve_host(hostname)
        except Exception:
            raise ValueError(f"Failed to resolve hostname: {hostname}")
            
        if not addrs:
            raise ValueError(f"No IP addresses found for hostname: {hostname}")
            
        valid_ip = None
        for ip in addrs:
            if is_global_public_ip(ip):
                valid_ip = ip
                break
        
        if valid_ip is None:
            raise ValueError(f"Non-public IP address found for hostname: {hostname}")
            
        return valid_ip

    # Parse initial URL
    parsed_url = urllib.parse.urlparse(url)
    
    # Validate initial URL
    validate_url(parsed_url)
    
    # Resolve and validate initial hostname
    resolved_ip = resolve_and_validate_hostname(parsed_url.hostname)
    
    # Build base URL for redirects
    base_url = f"{parsed_url.scheme}://{resolved_ip}"
    if parsed_url.path:
        base_url += parsed_url.path
    if parsed_url.query:
        base_url += f"?{parsed_url.query}"
    
    # Redirect handling
    max_redirects = 5
    current_url = url
    current_base = base_url
    
    for attempt in range(max_redirects):
        # Validate current URL again (in case of modification)
        parsed_url = urllib.parse.urlparse(current_url)
        validate_url(parsed_url)
        
        # Resolve and validate hostname for current URL
        resolved_ip = resolve_and_validate_hostname(parsed_url.hostname)
        
        # Update base URL for next iteration
        if attempt == 0:
            base_url = f"{parsed_url.scheme}://{resolved_ip}"
            if parsed_url.path:
                base_url += parsed_url.path
            if parsed_url.query:
                base_url += f"?{parsed_url.query}"
        
        # Make request
        try:
            req = urllib.request.Request(current_url)
            with urllib.request.urlopen(req) as response:
                status = response.status
                headers = dict(response.headers)
                body = response.read().decode('utf-8')
                
                if status != 200:
                    raise ValueError(f"Unexpected status code: {status}")
                
                return body
                
        except urllib.error.HTTPError as e:
            status = e.code
            if status == 301 or status == 302:
                location = e.headers.get('Location')
                if not location:
                    raise ValueError("Missing Location header in redirect")
                
                # Parse redirect location
                redirect_url = urllib.parse.urljoin(base_url, location)
                
                # Resolve hostname of redirect target
                redirect_parsed = urllib.parse.urlparse(redirect_url)
                if not redirect_parsed.hostname:
                    raise ValueError("Redirect target has no hostname")
                
                # Validate redirect URL
                validate_url(redirect_parsed)
                
                # Resolve and validate redirect hostname
                redirect_ip = resolve_and_validate_hostname(redirect_parsed.hostname)
                
                # Update base URL and current URL for next iteration
                if redirect_parsed.path:
                    new_base_url = f"{redirect_parsed.scheme}://{redirect_ip}{redirect_parsed.path}"
                    if redirect_parsed.query:
                        new_base_url += f"?{redirect_parsed.query}"
                else:
                    new_base_url = f"{redirect_parsed.scheme}://{redirect_ip}"
                
                if redirect_parsed.query:
                    new_base_url += f"?{redirect_parsed.query}"
                
                current_url = redirect_url
                current_base = new_base_url
                
                if attempt == max_redirects - 1:
                    raise ValueError("Maximum number of redirects exceeded")
                    
            else:
                raise ValueError(f"Unexpected status code: {status}")
        
        except urllib.error.URLError as e:
            raise ValueError(f"URL error: {e}")
    
    raise ValueError("Maximum number of redirects exceeded")
