import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.realpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                if not (member.isfile() or member.isdir()):
                    return False
                
                member_path = member.name
                
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        return False
                
                parts = member_path.split('/')
                filtered_parts = []
                for part in parts:
                    if part == '..':
                        return False
                    elif part != '.' and part != '':
                        filtered_parts.append(part)
                
                if member.isfile() and not filtered_parts:
                    return False
                
                target_path = os.path.join(dest_path, *filtered_parts)
                target_path = os.path.abspath(os.path.realpath(target_path))
                
                if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                    return False
                
                if member.isdir():
                    os.makedirs(target_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(target_path)
                    if not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    if not parent_dir.startswith(dest_path + os.sep) and parent_dir != dest_path:
                        return False
                    
                    source = tar.extractfile(member)
                    if source is None:
                        return False
                    
                    try:
                        with open(target_path, 'wb') as dest_file:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                dest_file.write(chunk)
                    finally:
                        source.close()
                    
                    if member.mode is not None:
                        os.chmod(target_path, member.mode)
    
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
    
    return True
