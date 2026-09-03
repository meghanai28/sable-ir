import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_name = member.name
                
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        member_name = '.'
                
                normalized_member = os.path.normpath(member_name)
                
                if normalized_member.startswith('..'):
                    return False
                
                if os.path.isabs(normalized_member):
                    return False
                
                full_extract_path = os.path.join(dest_path, normalized_member)
                full_extract_path = os.path.abspath(os.path.normpath(full_extract_path))
                
                real_dest_path = os.path.realpath(dest_path)
                real_extract_path = os.path.realpath(full_extract_path)
                
                if not real_extract_path.startswith(real_dest_path + os.sep) and real_extract_path != real_dest_path:
                    if os.path.isdir(real_dest_path) and real_extract_path == real_dest_path + os.sep:
                        pass
                    else:
                        return False
                
                if member.isdir():
                    os.makedirs(full_extract_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(full_extract_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(full_extract_path, 'wb') as out_f:
                            out_f.write(f.read())
                    
                    os.utime(full_extract_path, (member.mtime, member.mtime))
                else:
                    return False
        
        return True
    
    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
