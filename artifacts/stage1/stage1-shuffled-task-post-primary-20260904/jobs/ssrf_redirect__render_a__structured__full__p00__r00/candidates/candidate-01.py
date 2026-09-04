import os
import stat
import urllib.parse


def fetch_text(url, transport, resolve_host):
    parsed = urllib.parse.urlparse(url)
    
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")
    
    if parsed.scheme == 'http' and parsed.port is not None and parsed.port != 80:
        raise ValueError("HTTP must use default port 80")
    if parsed.scheme == 'https' and parsed.port is not None and parsed.port != 443:
        raise ValueError("HTTPS must use default port 443")
    
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("URL must have a hostname")
    
    resolved_ips = resolve_host(hostname)
    if not resolved_ips:
        raise ValueError("Could not resolve hostname")
    
    status, headers, body = transport(url)
    
    if status != 200:
        raise ValueError(f"Unexpected status code: {status}")
    
    return body


def read_report(filename, reports_root):
    reports_root = os.path.abspath(reports_root)
    
    if not os.path.isdir(reports_root):
        raise ValueError("reports_root must be a directory")
    
    if os.path.isabs(filename):
        raise ValueError("Absolute filenames are not allowed")
    
    if len(filename) >= 2 and filename[1] == ':':
        raise ValueError("Windows drive letters are not allowed")
    
    cursor = reports_root
    
    components = filename.split(os.sep)
    
    for i, component in enumerate(components):
        if component == '.' or component == '':
            continue
        
        if component == '..':
            cursor = os.path.dirname(cursor)
            if not cursor.startswith(reports_root) or (cursor == reports_root[:len(cursor)] and len(cursor) < len(reports_root)):
                raise ValueError("Path traversal outside reports_root")
            continue
        
        cursor = os.path.join(cursor, component)
        
        if os.path.islink(cursor):
            raise ValueError("Symbolic links are not allowed")
        
        if not os.path.exists(cursor) and i != len(components) - 1:
            continue
    
    if cursor == reports_root:
        raise ValueError("Request resolves to reports_root itself")
    
    if os.path.exists(cursor):
        file_stat = os.lstat(cursor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("Target is not an ordinary file")
    
    with open(cursor, encoding='utf-8') as f:
        return f.read()
