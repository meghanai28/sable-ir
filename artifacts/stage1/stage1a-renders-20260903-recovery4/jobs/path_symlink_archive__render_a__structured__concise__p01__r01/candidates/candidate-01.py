import os
import tarfile
from pathlib import Path


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest = Path(dest_path).resolve()
    
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf:
                # Reject symbolic links and hard links
                if member.issym() or member.islnk():
                    return False
                
                # Only permit regular files and directories
                if not (member.isfile() or member.isdir()):
                    return False
                
                # Resolve normalized absolute path against dest_path
                member_name = member.name
                if member_name.startswith('/'):
                    member_name = member_name[1:]
                
                # Prevent path traversal in member name
                parts = member_name.split('/')
                clean_parts = []
                for part in parts:
                    if part == '' or part == '.':
                        continue
                    if part == '..':
                        return False
                    clean_parts.append(part)
                
                if not clean_parts:
                    return False
                
                safe_name = '/'.join(clean_parts)
                target_path = (dest / safe_name).resolve()
                
                # Ensure the resolved path is strictly inside dest_path
                try:
                    target_path.relative_to(dest)
                except ValueError:
                    return False
                
                # Create parent directories
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError):
                    return False
                
                if member.isfile():
                    try:
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            data = fobj.read()
                        
                        # Write with restricted permissions, then restore
                        mode = member.mode
                        with open(target_path, 'wb') as f:
                            f.write(data)
                        
                        # Set permissions if needed (but don't make setuid/setgid)
                        if mode & 0o6000:
                            mode = mode & 0o0777
                        os.chmod(target_path, mode & 0o777)
                        
                    except (OSError, PermissionError, IOError):
                        return False
                    
                elif member.isdir():
                    try:
                        target_path.mkdir(parents=True, exist_ok=True)
                        mode = member.mode
                        if mode & 0o6000:
                            mode = mode & 0o0777
                        os.chmod(target_path, mode & 0o777)
                    except (OSError, PermissionError):
                        return False
        
        return True
        
    except (tarfile.TarError, OSError, PermissionError, IOError):
        return False
