import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(dest_path, member.name)
                normalized_member_path = os.path.abspath(os.path.normpath(member_path))
                
                if not normalized_member_path.startswith(dest_path + os.sep) and normalized_member_path != dest_path:
                    return False
                
                if member.isfile() or member.isdir():
                    try:
                        tar.extract(member, dest_path)
                    except Exception:
                        return False
                else:
                    return False
            
            return True
    except Exception:
        return False
