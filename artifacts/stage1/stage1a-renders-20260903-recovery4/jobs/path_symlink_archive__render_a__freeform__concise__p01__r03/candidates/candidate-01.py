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
                
                if normalized_member.startswith('..') or os.path.isabs(normalized_member):
                    return False
                
                full_path = os.path.join(dest_path, normalized_member)
                full_path = os.path.abspath(os.path.normpath(full_path))
                
                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    return False
                
                if member.isfile():
                    dir_path = os.path.dirname(full_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(full_path, 'wb') as out_f:
                            out_f.write(f.read())
                elif member.isdir():
                    os.makedirs(full_path, exist_ok=True)
                else:
                    return False
    except Exception:
        return False
    
    return True
