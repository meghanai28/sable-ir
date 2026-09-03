import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(dest_path)
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'
                
                parts = member_path.split('/')
                safe_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        safe_parts.append('..')
                    else:
                        safe_parts.append(part)
                
                safe_path = '/'.join(safe_parts)
                if safe_path.startswith('/'):
                    safe_path = safe_path[1:]
                
                resolved_path = os.path.join(dest_path, safe_path)
                resolved_path = os.path.normpath(resolved_path)
                
                if not resolved_path.startswith(dest_path + os.sep) and resolved_path != dest_path:
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(resolved_path)
                    if not parent_dir.startswith(dest_path + os.sep) and parent_dir != dest_path:
                        return False
            
            for member in members:
                if member.issym() or member.islnk():
                    return False
                
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'
                
                parts = member_path.split('/')
                safe_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    elif part == '..':
                        safe_parts.append('..')
                    else:
                        safe_parts.append(part)
                
                safe_path = '/'.join(safe_parts)
                if safe_path.startswith('/'):
                    safe_path = safe_path[1:]
                
                resolved_path = os.path.join(dest_path, safe_path)
                resolved_path = os.path.normpath(resolved_path)
                
                if not resolved_path.startswith(dest_path + os.sep) and resolved_path != dest_path:
                    return False
                
                if member.isdir():
                    os.makedirs(resolved_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(resolved_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    source = tar.extractfile(member)
                    if source is None:
                        return False
                    
                    try:
                        with open(resolved_path, 'wb') as target:
                            while True:
                                chunk = source.read(8192)
                                if not chunk:
                                    break
                                target.write(chunk)
                    finally:
                        source.close()
                    
                    if member.mode is not None:
                        os.chmod(resolved_path, member.mode)
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
