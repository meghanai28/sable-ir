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
                
                member_path = os.path.join(dest_path, member.name)
                normalized_member_path = os.path.abspath(member_path)
                
                if not normalized_member_path.startswith(dest_path + os.sep) and normalized_member_path != dest_path:
                    return False
                
                if member.isfile() or member.isdir():
                    pass
                else:
                    return False
            
            for member in members:
                member_path = os.path.join(dest_path, member.name)
                normalized_member_path = os.path.abspath(member_path)
                
                if member.isdir():
                    os.makedirs(normalized_member_path, exist_ok=True)
                elif member.isfile():
                    parent_dir = os.path.dirname(normalized_member_path)
                    os.makedirs(parent_dir, exist_ok=True)
                    
                    with tar.extractfile(member) as f:
                        if f is None:
                            return False
                        with open(normalized_member_path, 'wb') as out_f:
                            out_f.write(f.read())
            
            return True
            
    except (tarfile.TarError, OSError, IOError):
        return False
