import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False
                
                member_path = os.path.join(dest_path, member.name)
                normalized_path = os.path.abspath(os.path.normpath(member_path))
                
                if not normalized_path.startswith(dest_path + os.sep) and normalized_path != dest_path:
                    return False
                
                if member.isfile() or member.isdir():
                    tar.extract(member, dest_path)
                else:
                    return False
            
            return True
    except Exception:
        return False
