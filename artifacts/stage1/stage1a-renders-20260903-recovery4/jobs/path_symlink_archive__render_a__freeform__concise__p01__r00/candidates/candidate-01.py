import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
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
                
                full_extract_path = os.path.abspath(os.path.join(dest_path, normalized_member))
                
                if not full_extract_path.startswith(dest_path + os.sep) and full_extract_path != dest_path:
                    return False
                
                if member.isfile():
                    parent_dir = os.path.dirname(full_extract_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(full_extract_path, 'wb') as out_f:
                            out_f.write(f.read())
                
                elif member.isdir():
                    os.makedirs(full_extract_path, exist_ok=True)
                
                else:
                    return False
        
        return True
    
    except Exception:
        return False
