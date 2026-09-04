import logging
import re
import urllib.parse

def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Scheme must be HTTP or HTTPS")
    
    default_port = 80 if parsed.scheme == 'http' else 443
    
    port = parsed.port
    if port is None:
        port = default_port
    
    if port != default_port:
        raise ValueError("Port must be the default for the scheme")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must contain a hostname")
    
    ip_addresses = resolve_host(hostname)
    
    if not ip_addresses:
        raise ValueError("DNS resolution failed")
    
    for ip in ip_addresses:
        if not _is_valid_public_ip(ip):
            raise ValueError("Invalid or non-public IP address")
    
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Credentials in URL are not allowed")
    
    _configure_logging()
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Request failed with status {status}")
    
    return body

def _is_valid_public_ip(ip):
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        octets = []
        for part in parts:
            if not part.isdigit():
                return False
            val = int(part)
            if val < 0 or val > 255:
                return False
            octets.append(val)
        
        if octets[0] == 0:
            return False
        if octets[0] == 10:
            return False
        if octets[0] == 172 and 16 <= octets[1] <= 31:
            return False
        if octets[0] == 192 and octets[1] == 168:
            return False
        if octets[0] == 127:
            return False
        if octets[0] == 169 and octets[1] == 254:
            return False
        if octets[0] >= 224:
            return False
        
        return True
    except (ValueError, IndexError):
        return False

def _configure_logging():
    class SanitizingFilter(logging.Filter):
        def filter(self, record):
            msg = str(record.getMessage())
            
            msg = re.sub(r'(?i)(password|passwd|pwd)\s*[=:]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(bearer\s+)[a-zA-Z0-9\-_]+', r'\1<REDACTED>', msg)
            msg = re.sub(r'(?i)(session|sess|jsessionid|phpsessid)\s*[=:]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(private[_-]?key|privkey)\s*[=:]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(authorization[:=]\s*)(?:basic|bearer|digest|negotiate|ntlm|api-key|token)\s+[^\s&;]*', r'\1<REDACTED>', msg)
            msg = re.sub(r'(?i)(authorization[:=]\s*)[^\s&;]+', r'\1<REDACTED>', msg)
            msg = re.sub(r'(?i)(auth[:=]\s*)[^\s&;]+', r'\1<REDACTED>', msg)
            msg = re.sub(r'(?i)(token|access_token|refresh_token|id_token)\s*[=:]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(cookie[:=]\s*.*?)(?:session|sess|auth|token|id)=[^;]+', r'\1<REDACTED>', msg)
            msg = re.sub(r'(?i)(x-api-key|x-auth-token|x-csrf-token|x-access-token)\s*[:=]\s*[^\s&;]+', r'\1=<REDACTED>', msg)
            msg = re.sub(r'(?i)(key|secret|signature|sig)\s*[=:]\s*[a-zA-Z0-9\-_]{16,}', r'\1=<REDACTED>', msg)
            
            record.msg = msg
            record.args = ()
            
            return True
    
    for handler in logging.root.handlers:
        handler.addFilter(SanitizingFilter())
    
    if not logging.root.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(SanitizingFilter())
        logging.root.addHandler(handler)
    
    logging.root.setLevel(logging.INFO)
