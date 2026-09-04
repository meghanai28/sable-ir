import os
import re
from urllib.parse import urlparse

def fetch_text(url, transport, resolve_host):
    parsed = urlparse(url)
    
    scheme = parsed.scheme
    if scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must have a hostname")
    
    port = parsed.port
    if port is None:
        port = 443 if scheme == 'https' else 80
    
    default_port = 443 if scheme == 'https' else 80
    if port != default_port:
        raise ValueError("Only default ports are allowed")
    
    host_ip = resolve_host(hostname)
    
    netloc_with_port = f"{host_ip}:{port}"
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Userinfo in URL is not allowed")
    
    safe_path = parsed.path
    if parsed.query:
        safe_path = safe_path + '?' + parsed.query
    if parsed.fragment:
        safe_path = safe_path + '#' + parsed.fragment
    
    reconstructed_url = f"{scheme}://{netloc_with_port}{safe_path}"
    
    status, headers, body = transport(reconstructed_url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    if not isinstance(body, str):
        body = body.decode('utf-8')
    
    return body

def read_report(reports_root, filename):
    normalized = _lexical_normalize(filename)
    
    if os.path.isabs(normalized):
        raise ValueError("Absolute paths are not allowed")
    
    if normalized.startswith('..') or normalized == '..':
        raise ValueError("Path escapes root directory")
    
    candidate_path = os.path.join(reports_root, normalized)
    real_root = os.path.realpath(reports_root)
    real_candidate = os.path.realpath(candidate_path)
    
    if not real_candidate.startswith(real_root + os.sep) and real_candidate != real_root:
        raise ValueError("Path escapes root directory")
    
    current_path = reports_root
    segments = normalized.split(os.sep)
    
    for segment in segments:
        if segment == '' or segment == '.':
            continue
        
        current_path = os.path.join(current_path, segment)
        
        try:
            if os.path.islink(current_path):
                raise ValueError("Symbolic link detected in path")
        except OSError:
            pass
    
    with open(candidate_path, 'r', encoding='utf-8') as f:
        return f.read()

def _lexical_normalize(path):
    result = []
    segments = path.replace('\\', '/').split('/')
    
    for segment in segments:
        if segment == '' or segment == '.':
            continue
        elif segment == '..':
            if result:
                result.pop()
        else:
            result.append(segment)
    
    normalized = '/'.join(result)
    return normalized
